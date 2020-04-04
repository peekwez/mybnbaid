import arrow

import rock as rk

from . import exceptions as exc
from . import text as txt


MAX_WORKERS = 2


class BookingsService(rk.svc.BaseService):
    _name = 'bookings'
    _version = '0.0.1'
    _users_rpc = None
    _sms_rpc = None
    _properties_rpc = None
    _cleans_rpc = None

    def _setup_clients(self, broker, verbose):
        self._users_rpc = rk.rpc.RpcProxy(broker, 'users', verbose)
        self._sms_rpc = rk.rpc.RpcProxy(broker, 'sms', verbose)
        self._properties_rpc = rk.rpc.RpcProxy(broker, 'properties', verbose)
        self._cleans_rpc = rk.rpc.RpcProxy(broker, 'cleans', verbose)

    def _send_sms(self, user, clean, template):
        if user == 'host':
            user_id = clean['host_id']
        elif user == 'aid':
            user_id = clean['aid_id']

        aid = self._users_rpc.get_phone_number(user_id=user_id)
        context = (clean['property']['street'], clean['date'])
        message = template.format(*context)
        return self._sms_rpc.send(
            number=phone_number,
            message=message
        )

    def _check_owner(self, user, user_id, zone, clean_id):
        clean = self._db.get(zone, 'bookings', clean_id)
        if clean[f'{user}_id'] != user_id:
            raise exc.NotOwner('user cannot modify this resource')
        return clean

    def book_clean(self, user_id, property_id, datetime, notes=None):  # host
        prop = self._properties_rpc.get_property(
            user_id=user_id, property_id=property_id
        )
        for key in ('created', 'updated'):
            prop.pop(key)

        data = dict(
            property_id=property_id, property=prop,
            host_id=user_id, aid_id=0, datetime=datetime,
            notes=notes, zone=prop['zone']
        )
        clean = self._repo.put(prop['zone'], 'bookings', data)
        return clean

    def cancel_clean(self, user_id, zone, clean_id):
        clean = self._check_owner('host', user_id, zone, clean_id)
        if clean['aid_id'] == 0:
            return self._repo.drop(zone, 'bookings', clean_id)

        clean['is_cancelled'] = True
        data = dict(user_id=user_id, data=clean)
        clean = self._cleans_rpc.create_clean(user_id, data=clean)
        res = self._send_sms('aid', clean, txt.CANCELLED)
        return clean

    def update_clean(self, user_id, zone, clean_id, datetime, notes=None):  # host
        _ = self._check_owner('host', user_id, zone, clean_id)
        data = dict(datetime=datetime, notes=notes)
        clean = self._repo.edit(zone, 'bookings', clean_id, data)
        if clean['aid_id'] != 0:
            self._send_sms('aid', clean, txt.UPDATED)
        return clean

    def accept_clean(self, user_id, zone, clean_id):
        data = dict(aid_id=user_id)  # any one can accept
        clean = self._repo.edit(zone, 'bookings', clean_id, data)
        res = self._send_sms('host', clean, txt.ACCEPTED)
        return clean

    def reject_clean(self, user_id, zone, clean_id):
        _ = self._check_owner('aid', user_id, zone, clean_id)
        data = dict(aid_id=0)
        clean = self._repo.edit(schema, 'bookings', clean_id, data)
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
        clean = self._cleans_rpc.create_clean(user_id=user_id, data=clean)
        res = self._send_sms('host', clean, txt.COMPLETED)
        res = self._repo.drop(zone, 'bookings', clean_id)
        return clean

    def get_clean(self, user_id, zone, clean_id):
        clean = self._repo.get(zone, 'bookings', clean_id)
        return clean

    def get_zone_cleans(self, user_id, zone, limit=20, offset=0):
        # add a filter indicator for week availability
        # and hour and minute
        kwargs = dict(offset=offset, limit=limit)
        params = (('aid_id',), (0,))
        cleans = self._db.filter(zone, 'bookings', params, **kwargs)
        return cleans

    def get_aid_cleans(self, user_id, zone, limit=20, offset=0):
        params = (('aid_id',), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        cleans = self._repo.filter(zone, 'bookings', params, **kwargs)
        return cleans

    def get_property_cleans(self, user_id, zone, property_id, limit=20, offset=0):
        params = (('property_id',), (property_id,))
        kwargs = dict(offset=offset, limit=limit)
        cleans = self._repo.filter(zone, 'bookings', params, **kwargs)
        return cleans


def main():
    conf = rk.utils.parse_config()
    with BookingsService(conf) as service:
        service()


if __name__ == "__main__":
    main()
