import backless as bk

from . import exceptions as exc


class PropertiesService(bk.svc.BaseService):
    _name = 'properties'
    _version = '0.0.1'
    _schema = 'properties'
    _zones_rpc = None

    def _setup_clients(self, broker, verbose):
        self._zones_rpc = bk.rpc.RpcProxy(
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
        prop = self._repo.put(self._schema, 'properties', data)
        return prop

    def update_property(self, user_id, property_id, street, city, postcode, country, bedrooms, washrooms, size):
        data = self._property(
            user_id, street, city, postcode, country, bedrooms, washrooms, size
        )
        prop = self._repo.edit(self._schema, 'properties', property_id, data)
        return prop

    def get_property(self, user_id, property_id):
        prop = self._repo.get(self._schema, 'properties', property_id)
        return prop

    def list_properties(self, user_id, limit=20, offset=0):
        params = dict(user_id=user_id)
        kwargs = dict(offset=offset, limit=limit)
        props = self._repo.filter(self._schema, 'properties', params)
        return props

    def delete_property(self, user_id, property_id):
        self._repo.drop(self._schema, 'properties', property_id)
        return {}


def main():
    bk.utils.start_service(PropertiesService)


if __name__ == "__main__":
    main()
