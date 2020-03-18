from . import base
from . import mapping

import rock as rk


class UsersNoAuthHandler(base.BaseHandler):
    _client = rk.mdp.mdcliapi2.MajorDomoClient(
        "tcp://localhost:5555", b'users', False
    )
    _name = b'users'


class UsersHandler(base.BaseAuthHandler):
    _client = rk.mdp.mdcliapi2.MajorDomoClient(
        "tcp://localhost:5555", b'users', False
    )
    _name = b'users'
