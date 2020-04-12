import backless as bk

from . import exceptions as exc
from . import store as store

MAX_WORKERS = 2


def strip_arn(zone, fields=('subscription_arn',)):
    [zone.pop(key, None) for key in fields]
    return zone


class Tasks(bk.svc.BaseTasks):
    def __init__(self, sns, topics, repo, schema):
        self._sns = sns
        self._topics = topics
        self._repo = repo
        self._schema = schema

    def subscribe_number(self, data):
        name = data['topic'].replace(' ', '')
        response = self._sns.subscribe(
            TopicArn=self._topics[name],
            Endpoint=data['number'],
            Protocol='sms'
        )
        code, arn = bk.utils.parse_response(
            response, extras=['SubscriptionArn']
        )
        if code == 200 and arn:
            data = {'subscription_arn': arn}
            zone = self._repo.edit(
                self._schema, 'zones', data['zone_id'], data
            )

    def unsubscribe_number(self, data):
        response = self._sns.unsubscribe(
            SubscriptionArn=data['arn']
        )


class ZonesService(bk.svc.BaseService):
    _name = 'zones'
    _version = '0.0.1'
    _schema = 'zones'
    _users_rpc = None

    def __init__(self, conf):
        super(ZonesService, self).__init__(conf)
        sns, topics = self._sas.get_client('sns', region='us-east-1')
        self._update_topics(sns, topics)
        self._setup_tasks(
            Tasks(sns, topics, self._repo, self._schema),
            MAX_WORKERS,
        )

    def __exit__(self, type, value, traceback):
        store.memdata.close()
        super(ZonesService, self).__exit__(type, value, traceback)

    def _setup_clients(self, broker, verbose):
        self._users_rpc = bk.rpc.RpcProxy(
            broker, 'users', verbose
        )

    def _update_topics(self, sns, topics):
        zones = self.get_regions(user_id=b'zones')['items']
        current = set(topics.keys())
        update = {zone['region'] for zone in zones}
        latest = update - current
        for topic in latest:
            arn = self._create_topic(sns, topic)
        self._log.info('zone topics are up to date')

    def _create_topic(self, sns, topic):
        name = topic.replace(' ', '')
        try:
            kwargs = {'DisplayName': topic}
            res = sns.create_topic(
                Name=name, Attributes=kwargs
            )
        except Exception as err:
            self._log.exception(err)
            return None
        else:
            return res['TopicArn']

    def add_zone(self, user_id, region):
        user = self._users_rpc.get_phone_number(
            user_id=user_id
        )
        if not user.get('phone_number'):
            raise ZoneError('phone number required to add zones')

        data = dict(user_id=user_id, name=region)
        zone = self._repo.put(self._schema, 'zones', data)
        data = dict(
            topic=region, number=user['phone_number'],
            zone_id=zone['id']
        )
        res = self._emit('subscribe:number', data)
        return zone

    def get_zone(self, user_id, zone_id):
        zone = self._repo.get(self._schema, 'zones', zone_id)
        return strip_arn(zone)

    def list_zones(self, user_id, limit=20, offset=0):
        params = (('user_id',), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        zones = self._repo.filter(self._schema, 'zones', params, **kwargs)
        items = [strip_arn(zone) for zone in zones['items']]
        zones['items'] = items
        return zones

    def delete_zone(self, user_id, zone_id):
        zone = self._repo.get(self._schema, 'zones', zone_id)
        arn = zone.get('subscription_arn', None)
        if arn:
            data = dict(arn=arn)
            res = self._emit('unsubscribe:number', data)
        self._repo.drop(self._schema, 'zones', zone_id)
        return {}

    def get_location(self, user_id, fsa):
        return store.memdata.location(fsa)

    def get_city(self, user_id, fsa):
        return store.memdata.city(fsa)

    def get_region(self, user_id, fsa):
        return store.memdata.region(fsa)

    def get_locations(self, user_id):
        return store.memdata.locations()

    def get_cities(self, user_id):
        return store.memdata.cities()

    def get_regions(self, user_id):
        return store.memdata.regions()


def main():
    conf = bk.utils.parse_config()
    with ZonesService(conf) as service:
        service()


if __name__ == "__main__":
    main()
