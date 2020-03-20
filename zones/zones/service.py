import rock as rk

from . import exceptions as exc
from . import store as db


class ZonesService(rk.utils.BaseService):
    _name = b'zones'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(ZonesService, self).__init__(brokers, conf, verbose)
        self._db = db.ZonesStore()  # sqlite in memory store

    def get_location(self, user_id, fsa):
        return self._db.location(fsa)

    def get_city(self, user_id, fsa):
        return self._db.city(fsa)

    def get_region(self, user_id, fsa):
        return self._db.region(fsa)

    def get_locations(self, user_id):
        return self._db.locations()

    def get_cities(self, user_id):
        return self._db.cities()

    def get_regions(self, user_id):
        return self._db.regions()


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['zones']
    with ZonesService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
