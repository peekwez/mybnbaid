# create a materialized view for each region with no data --NO DATA
# this materialized view is for all opened cleans
import collections
import arrow
import rock as rk

from . import exceptions as exc
from . import text as txt

ViewParser = collections.namedtuple(
    'ViewParser', ('zone',)
)
MAX_WORKERS = 4


class BookingsConsumer(rk.utils.BaseConsumer):
    def __init__(self, addr, name, db):
        super(ZonesConsumer, self).__init__(addr, name)
        dsn = rk.aws.get_db_secret(name)
        self._db = rk.utils.DB[db](dsn)

    def create(self, data):
        opts = ViewParser(**data)
        params = (('aid_id',)(0,))
        res = self._db.create_view(
            opts.schema, 'bookings', params
        )
        code = 200 if res else 400
        return code

    def refresh(self, data):
        opts = ViewParser(**data)
        fields = ('aid_id',)
        res = self._db.refresh_view(
            opts.schema, 'bookings', fields
        )
        code = 200 if res else 400
        return code


class BookingsService(rk.utils.BaseService):
    _name = b'bookings'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(BookingsService, self).__init__(brokers, conf, verbose)

    def _send_sms(self, user, clean, template):
        if user == 'host':
            user_id = clean['host_id']
        elif user == 'aid':
            user_id = clean['aid_id']

        data = dict(user_id=user_id)
        aid = self._send(b'users', 'get_phone_number', data)
        context = (clean['property']['street'], clean['date'])
        message = template.format(*context)
        data = dict(number=phone_number, message=message)
        return self._send(b'sms', 'send', data)

    def _check_owner(self, user, user_id, zone, clean_id):
        clean = self._db.get(zone, 'bookings', clean_id)
        if clean[f'{user}_id'] != user_id:
            raise exc.NotOwner('user cannot modify this resource')
        return clean

    def book_clean(self, user_id, property_id, datetime, notes=None):  # host
        data = dict(user_id=user_id, property_id=property_id)
        prop = self._send(b'properties', 'get_property', data)
        for key in ('created', 'updated'):
            prop.pop(key)

        data = dict(
            property_id=property_id, property=prop,
            host_id=user_id, aid_id=0, datetime=datetime,
            notes=notes, zone=prop['zone']
        )
        clean = self._db.create(prop['zone'], 'bookings', data)
        return clean

    def cancel_clean(self, user_id, zone, clean_id):
        clean = self._check_owner('host', user_id, zone, clean_id)
        if clean['aid_id'] == 0:
            return self._db.delete(zone, 'bookings', clean_id)

        clean['is_cancelled'] = True
        data = dict(user_id=user_id, data=clean)
        clean = self._send(b'cleans', 'create_clean', data)
        res = self._send_sms('aid', clean, txt.CANCELLED)
        return clean

    def update_clean(self, user_id, zone, clean_id, datetime, notes=None):  # host
        _ = self._check_owner('host', user_id, zone, clean_id)
        data = dict(datetime=datetime, notes=notes)
        clean = self.db.update(zone, 'bookings', clean_id, data)
        if clean['aid_id'] != 0:
            self._send_sms('aid', clean, txt.UPDATED)
        return clean

    def accept_clean(self, user_id, zone, clean_id):
        data = dict(aid_id=user_id)  # any one can accept
        clean = self.db.update(zone, 'bookings', clean_id, data)
        res = self._send_sms('host', clean, txt.ACCEPTED)
        return clean

    def reject_clean(self, user_id, zone, clean_id):
        _ = self._check_owner('aid', user_id, zone, clean_id)
        data = dict(aid_id=0)
        clean = self.db.update(schema, 'bookings', clean_id, data)
        res = self._send_sms('host', clean, txt.REJECTED)
        return {}

    def complete_clean(self, user_id, zone, clean_id, comments=None):  # aid
        clean = self._check_owner('aid', user_id, zone, clean_id)
        datetime = arrow.get(clean['datetime'])
        today = arrow.now(datetime.tzinfo)
        if datetime >= today:
            exc.NotAllowed('clean cannot be completed at this time')

        clean['is_completed'] = True
        clean['comments'] = comments
        data = dict(user_id=user_id, data=clean)
        clean = self._send(b'cleans', 'create_clean', data)

        res = self._send_sms('host', clean, txt.COMPLETED)
        res = self._db.delete(zone, 'bookings', clean_id)
        return clean
