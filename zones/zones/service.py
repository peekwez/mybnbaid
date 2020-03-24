import collections

import rock as rk

from . import exceptions as exc
from . import store as store

_schema = 'zones'

SNSParser = collections.namedtuple(
    'SNSParser', ('topic', 'number', 'zone_id')
)
ARNParser = collections.namedtuple(
    'ARNParser', ('arn',)
)
MAX_WORKERS = 2


def strip_arn(zone, fields=('subscription_arn',)):
    [zone.pop(key, None) for key in fields]
    return zone


class ZonesConsumer(rk.utils.BaseConsumer):
    def __init__(self, db, addr, name):
        super(ZonesConsumer, self).__init__(addr, name)
        self._sns, self._topics = rk.aws.get_client(
            'sns', use_session=False, region='us-east-1'
        )
        dsn = rk.aws.get_db_secret(name)
        self._db = rk.utils.DB[db](dsn)

    def subscribe(self, data):
        opts = SNSParser(**data)
        name = opts.topic.replace(' ', '')
        response = self._sns.subscribe(
            TopicArn=self._topics[name],
            Endpoint=opts.number,
            Protocol='sms'
        )
        code, arn = rk.aws.parse_response(
            response, extras=['SubscriptionArn']
        )
        if code == 200 and arn:
            data = {'subscription_arn': arn}
            zone = self._db.update(
                _schema, 'zones', opts.zone_id, data
            )

        return code

    def unsubscribe(self, data):
        opts = ARNParser(**data)
        response = self._sns.unsubscribe(
            SubscriptionArn=opts.arn
        )
        return rk.aws.parse_response(response)


class ZonesService(rk.utils.BaseService):
    _name = b'zones'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(ZonesService, self).__init__(brokers, conf, verbose)
        self._mem = store.ZonesStore()  # sqlite in memory store
        self.__update_topics()
        self._setup_events(
            (rk.utils.BaseProducer,),
            (ZonesConsumer, conf.get('db')),
            MAX_WORKERS
        )

    def __exit__(self, type, value, traceback):
        self._mem.close()
        super(ZonesService, self).__exit__(type, value, traceback)

    def __update_topics(self):
        sns, topics = rk.aws.get_client(
            'sns', use_session=False, region='us-east-1'
        )
        zones = self.get_regions(user_id=b'zones')['items']
        current = set(topics.keys())
        update = {zone['region'] for zone in zones}
        latest = update - current
        for topic in latest:
            arn = self.__create_topic(sns, topic)
        self._log.info('zone topics are up to date')

    def __create_topic(self, sns, topic):
        name = topic.replace(' ', '')
        try:
            kwargs = {'DisplayName': topic}
            res = sns.create_topic(Name=name, Attributes=kwargs)
        except Exception as err:
            self._log.exception(err)
            return None
        else:
            return res['TopicArn']

    def add_zone(self, user_id, region):
        data = {'user_id': user_id}
        user = self._send(b'users', 'get_phone_number', data)
        if not user.get('phone_number'):
            raise ZoneError('phone number required to add zones')

        data['name'] = region
        zone = self._db.create(_schema, 'zones', data)
        data = dict(
            topic=region, number=user['phone_number'],
            zone_id=zone['id']
        )

        res = self._emit('subscribe', data)
        return zone

    def get_zone(self, user_id, zone_id):
        zone = self._db.get(_schema, 'zones', zone_id)
        return strip_arn(zone)

    def list_zones(self, user_id, limit=20, offset=0):
        params = (('user_id',), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        zones = self._db.filter(_schema, 'zones', params, **kwargs)
        items = [strip_arn(zone) for zone in zones['items']]
        zones['items'] = items
        return zones

    def delete_zone(self, user_id, zone_id):
        zone = self._db.get(_schema, 'zones', zone_id)
        arn = zone.get('subscription_arn', None)
        if arn:
            data = dict(arn=arn)
            res = self._emit('unsubscribe', data)
        self._db.delete(_schema, 'zones', zone_id)
        return {}

    def get_location(self, user_id, fsa):
        return self._mem.location(fsa)

    def get_city(self, user_id, fsa):
        return self._mem.city(fsa)

    def get_region(self, user_id, fsa):
        return self._mem.region(fsa)

    def get_locations(self, user_id):
        return self._mem.locations()

    def get_cities(self, user_id):
        return self._mem.cities()

    def get_regions(self, user_id):
        return self._mem.regions()


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['zones']
    with ZonesService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
