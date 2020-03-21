import zmq
import collections
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop
from multiprocessing import Process, Pool

import rock as rk

from . import exceptions as exc
from . import store as store

_schema = 'zones'

SNSParser = collections.namedtuple(
    'SNSParser', ('action', 'topic', 'number', 'zone_id')
)
ARNParser = collections.namedtuple(
    'ARNParser', ('action', 'arn')
)
MAX_WORKERS = 2


def consumer(addr, name, client):
    log = rk.utils.logger('sms.service')
    sns, topics = rk.aws.get_client(
        'sns', use_session=False, region='us-east-1'
    )
    dsn = rk.aws.get_db_secret(name)
    db = rk.utils.DB[client](dsn)

    def subscribe(topic, number, zone_id):
        name = topic.replace(' ', '')
        response = sns.subscribe(
            TopicArn=topics[name],
            Endpoint=number,
            Protocol='sms'
        )
        arn = response.get('SubscriptionArn')
        meta = response.get('ResponseMetadata')

        data = {'subscription_arn': arn}
        zone = db.update(_schema, 'zones', zone_id, data)

        return meta.get('HTTPStatusCode')

    def unsubscribe(arn):
        response = sns.unsubscribe(SubscriptionArn=arn)
        meta = response.get('ResponseMetadata')
        return meta.get("HTTPStatusCode")

    def handler(message):
        data = rk.msg.unpack(message[-1])
        try:
            if data['action'] == 'subscribe':
                req = SNSParser(**data)
                code = subscribe(req.topic, req.number, req.zone_id)
            elif data['action'] == 'unsubscribe':
                req = ARNParser(**data)
                code = unsubscribe(req.arn)
        except Exception as err:
            log.exception(err)
            result = 'failed...'
        else:
            if code == 200:
                result = 'passed...'
        finally:
            log.info(f'{req.action} to zone {result}')

    ctx, sock = rk.zkit.consumer(addr, handler)
    log.info('consumer started...')

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('consumer interrupted...')
    finally:
        log.info('closing consumer sockets...')
        sock.close()
        if ctx:
            ctx.term()
        if db:
            db.close()


def strip_arn(zone, fields=('subscription_arn',)):
    [zone.pop(key, None) for key in fields]
    return zone


class ZonesService(rk.utils.BaseService):
    _name = b'zones'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(ZonesService, self).__init__(brokers, conf, verbose)
        self._mem = store.ZonesStore()  # sqlite in memory store
        self.__update_topics()

        self._setup_ipc()
        self._ctx, self._producer = rk.zkit.producer(self._ipc)
        self._log.info('zones producer started...')

        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (
                Process(
                    target=consumer,
                    args=(self._ipc, 'zones', conf.get('db'))),)

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

    def __send_request(self, data):
        self._producer.send(rk.msg.pack(data))
        res = {
            'ok': True, 'details': f"{data['action']} submitted..."
        }
        return res

    def add_zone(self, user_id, region):
        data = {'user_id': user_id}
        req = rk.msg.prepare('get_phone_number', data)
        user = rk.msg.unpack(
            self._clients['users'].send(b'users', req)[-1]
        )
        if not user.get('phone_number'):
            raise ZoneError('phone number required to add zones')

        data['name'] = region
        zone = self._db.create(_schema, 'zones', data)
        data = {
            'action': 'subscribe',
            'topic': region,
            'number': user['phone_number'],
            'zone_id': zone['id']
        }
        res = self.__send_request(data)
        return zone

    def get_zone(self, user_id, zone_id):
        zone = self._db.get(_schema, 'zones', zone_id)
        return strip_arn(zone)

    def list_zones(self, user_id, limit=20, offset=0):
        params = (('user_id',), (user_id,))
        kwargs = {'offset': offset, 'limit': limit}
        zones = self._db.filter(_schema, 'zones', params, **kwargs)
        items = [strip_arn(zone) for zone in zones['items']]
        zones['items'] = items
        return zones

    def delete_zone(self, user_id, zone_id):
        zone = self._db.get(_schema, 'zones', zone_id)
        data = {
            'action': 'unsubscribe',
            'arn': zone['subscription_arn']
        }
        res = self.__send_request(data)
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
