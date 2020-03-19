import rock as rk

from . import exceptions as exc
from . import store as db


class ZonesService(rk.utils.BaseService):
    _name = b'zones'
    _version = b'0.0.1'
    _log = rk.utils.logger('zones.service')

    def __init__(self, brokers, conf, verbose):
        super(ZonesService, self).__init__(brokers, conf, verbose)
        self._db = db.ZonesStore()  # sqlite in memory store

    def get_location(self, fsa):
        return self._db.zones.location(fsa)

    def get_city(self, fsa):
        return self._db.zones.city(fsa)

    def get_region(self, fsa):
        return self._db.zones.region(fsa)

    def get_locations(self):
        return self._db.zones.locations()

    def get_cities(self, fsa):
        return self._db.zones.cities(fsa)

    def get_regions(self, fsa):
        return self._db.zones.regions(fsa)


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['zones']
    with ZonesService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
