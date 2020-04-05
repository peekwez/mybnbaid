import rock as rk

from . import exceptions as exc

_schema = 'properties'


class PropertiesService(rk.svc.BaseService):
    _name = 'properties'
    _version = '0.0.1'
    _zones_rpc = None

    def _setup_clients(self, broker, verbose):
        self._zones_rpc = rk.rpc.RpcProxy(
            broker, 'zones', verbose
        )

    def _property(self, user_id, street, city, postcode, country, bedrooms, washrooms, size):
        zone = self._zones_rpc.get_region(
            user_id=user_id, fsa=postcode[:3]
        )
        data = dict(
            user_id=user_id, street=street, city=city,
            postcode=postcode, country=country,
            bedrooms=bedrooms, washrooms=washrooms,
            size=size, zone=zone['region']
        )
        return data

    def add_property(self, user_id, street, city, postcode, country, bedrooms, washrooms, size):
        data = self._property(
            user_id, street, city, postcode, country, bedrooms, washrooms, size
        )
        prop = self._repo.put(_schema, 'properties', data)
        return prop

    def update_property(self, user_id, property_id, street, city, postcode, country, bedrooms, washrooms, size):
        data = self._property(
            user_id, street, city, postcode, country, bedrooms, washrooms, size
        )
        prop = self._repo.edit(_schema, 'properties', property_id, data)
        return prop

    def get_property(self, user_id, property_id):
        prop = self._repo.get(_schema, 'properties', property_id)
        return prop

    def list_properties(self, user_id, limit=20, offset=0):
        params = (('user_id',), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        props = self._repo.filter(_schema, 'properties', params)
        return props

    def delete_property(self, user_id, property_id):
        self._repo.drop(_schema, 'properties', property_id)
        return {}


def main():
    conf = rk.utils.parse_config()
    with PropertiesService(conf) as service:
        service()


if __name__ == "__main__":
    main()
