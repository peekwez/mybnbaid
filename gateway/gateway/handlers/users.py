from . import base
from . import mapping

import rock as rk


class UsersNoAuthHandler(base.BaseHandler):
    _service = b'users'


class UsersHandler(base.BaseAuthHandler):
    _service = b'users'
