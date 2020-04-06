from . import base


class ZonesHandler(base.BaseHandler):
    _service = 'zones'


handlers = [
    (r'/zones.info', ZonesHandler, dict(rpc='info', auth=False)),
    (r'/zones.getLocation', ZonesHandler, dict(rpc='get_location')),
    (r'/zones.getCity', ZonesHandler, dict(rpc='get_city')),
    (r'/zones.getRegion', ZonesHandler, dict(rpc='get_region')),
    (r'/zones.locations', ZonesHandler, dict(rpc='get_locations')),
    (r'/zones.cities', ZonesHandler, dict(rpc='get_cities')),
    (r'/zones.regions', ZonesHandler, dict(rpc='get_regions')),
]
