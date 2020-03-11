import zmq

from tornado import ioloop

#import firebase_admin
#from firebase_admin import auth as _auth

import schemaless as sm
import rock as rk

from . import exceptions as exc
from . import authentication as _auth

# logging variables
_log = rk.utils.logger('users.service', 'INFO')
_url = 'https://api.mybnbaid.com'

# message format
_msg = rk.msg.Client(b'mpack')

# zmq variables
_ctx = zmq.Context()
_server = None
_auth_producer = None

# datastore variables
_store = None
_schema = 'users'


#_app = firebase_admin.initialize_app()

# rpc api endpoints
rpc = rk.utils.RPC()  # OrderedDict()


def strip_sensitive(user, fields=('id', 'password', 'salt')):
    [user.pop(key) for key in fields]
    return user


def handler(message):
    rk.utils.handle(rpc, _server, _msg, message, log=_log)


def _setup(addr, dsn):
    global _server, _store
    _server = rk.zkit.router(_ctx, addr, handler=handler)
    _store = sm.client.PGClient(dsn)


def find_by_email(email):
    return _store.filter(_schema, 'users', (('email',), (email,)))


@rpc.register('/users.create')
def create_user(email, password):
    user = find_by_email(email)
    if user:
        raise exc.EmailTaken('email address is taken')

    data = {"email": email}
    salt, hashed = _auth.encrypt(password)
    data.update({'salt': salt, 'password': hashed})

    user = _store.create(_schema, 'users', data)
    user = _auth.login(user, password)

    passed = _auth.request_verify_email(user['id'], user['email'])
    return strip_sensitive(user)


@rpc.register('/users.setName')
def set_name(user_id, first_name, last_name):
    data = {'first_name': first_name, 'last_name': last_name}
    user = _store.update(_schema, 'users', user_id, data)
    return strip_sensitive(user)


@rpc.register('/users.setPhoneNumber')
def set_phone_number(user_id, phone_number):
    data = {'phone_number': phone_number}
    user = _store.update(_schema, 'users', user_id, data)
    return strip_sensitive(user)


@rpc.register('/users.address.create')
def create_address(user_id, street, city, postcode, country):
    data = {
        'user_id': user_id, 'street': street,
        'city': city, 'postcode': postcode,
        'country': country
    }
    address = _store.create(_schema, 'address', data)
    return address


@rpc.register('/users.address.update')
def update_address(addr_id, street, city, postcode, country):
    data = {
        'street': street, 'city': city,
        'postcode': postcode, 'country': country
    }
    address = _store(_schema, 'address', addr_id, data)
    return address


@rpc.register('/users.address.list')
def list_address(user_id, limit=20, offset=0):
    params = (("user_id",), (user_id,))
    addresses = _store.filter(
        _schema, 'address', params, **kwargs
    )
    return addresses


@rpc.register('users.address.delete')
def delete_address(addr_id):
    _store.delete(_schema, 'address', addr_id)


@rpc.register('/users.delete')
def delete_user(user_id):
    data = {'disabled': True}
    _store.update(_schema, 'users', user_id, data)


@rpc.register('/users.auth.login')
def login_user(email, password):
    user = find_by_email(email)
    user = _auth.login(user, password)
    return strip_sensitive(user)


@rpc.register('/users.auth.requestVerifyEmail')
def request_verify_email(user_id):
    user = _store.get(_schema, 'users', user_id)
    passed = _auth.request_verify_email(user_id, user['email'])
    return {'passed': True}


@rpc.register('/users.auth.setEmailVerified')
def set_email_verified(token):
    data = _auth.verify_email(_store, token)
    return data


@rpc.register('/users.auth.requestPasswordReset')
def request_password_reset(email):
    user = find_by_email(email)
    passed = _auth.request_password_reset(_store, user['id'])
    return {'passed': True}


@rpc.register('/users.auth.setPassword')
def reset_password(token, password):
    passed = _auth.reset_password(_store, token, password)
    return {'passed': True}


def start(addr, dsn):
    _log.info('starting users service...')
    _setup(addr, dsn)
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('user service interrupted')
        _store.close()


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-ip', '--addr', dest='addr',
        help='service end point',
        default='tcp://127.0.0.1:5000'
    )

    parser.add_argument(
        '-dsn', '--dsn', dest='dsn',
        help='database address',
        default='postgres://postgres:password@127.0.0.1:5433/schemaless'
    )

    options = parser.parse_args()
    start(options.addr, options.dsn)


if __name__ == "__main__":
    main()
