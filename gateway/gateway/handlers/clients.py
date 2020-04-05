from . import base
from . import mapping

import rock as rk


class UsersNoAuthHandler(base.BaseHandler):
    _service = 'users'


class ZonesNoAuthHandler(base.BaseHandler):
    _service = 'zones'


class PropertiesNoAuthHandler(base.BaseHandler):
    _service = 'properties'


class BookingsNoAuthHandler(base.BaseHandler):
    _service = 'bookings'


class CleansNoAuthHandler(base.BaseHandler):
    _service = 'cleans'


class UsersHandler(base.BaseAuthHandler):
    _service = 'users'


class ZonesHandler(base.BaseAuthHandler):
    _service = 'zones'


class PropertiesHandler(base.BaseAuthHandler):
    _service = 'properties'


class BookingsHandler(base.BaseAuthHandler):
    _service = 'bookings'


class CleansHandler(base.BaseAuthHandler):
    _service = 'cleans'
