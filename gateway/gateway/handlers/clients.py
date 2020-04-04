from . import base
from . import mapping

import rock as rk


class UsersNoAuthHandler(base.BaseHandler):
    _service = 'users'


class UsersHandler(base.BaseAuthHandler):
    _service = 'users'


class ZonesHandler(base.BaseAuthHandler):
    _service = 'zones'
