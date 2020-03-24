import rock as rk

from . import exceptions as exc

_schema = 'properties'


class PropertiesService(rk.utils.BaseService):
    _name = b'properties'
    _version = b'0.0.1'

    def __property(self, user_id, street, city, postcode, country, bedrooms, washrooms, size):
        data = dict(user_id=user_id, fsa=postcode[:3])
        zone = self._send(b'zones', 'get_region', data)
        data = dict(
            user_id=user_id, street=street, city=city,
            postcode=postcode, country=country,
            bedrooms=bedrooms, washrooms=washrooms,
            size=size, zone=zone['region']
        )
        return data

    def add_property(self, user_id, **kwargs):
        data = self.__property(user_id, **kwargs)
        prop = self._db.create(_schema, 'properties', data)
        return prop

    def update_property(self, user_id, property_id, **kwargs):
        data = self.__property(user_id, **kwargs)
        prop = self._db.update(_schema, 'properties', property_id, data)
        return prop

    def get_property(self, user_id, property_id):
        prop = self._db.get(_schema, 'properties', property_id)
        return prop

    def list_properties(self, user_id, limit=20, offset=0):
        params = (('user_id',), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        props = self._db.filter(schema, 'properties', params)
        return props

    def delete_property(self, user_id, property_id):
        self._db.delete(_schema, 'properties', property_id)
        return {}


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['properties']
    with PropertiesService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
