import zmq

from tornado import ioloop

import schemaless as sm
import rock as rk

from . import exceptions as exc
from . import authentication as _auth

# logging variables
_log = rk.utils.logger('users.service', 'INFO')
_url = 'https://api.mybnbaid.com'

# message format
_proto = rk.msg.Client(b'mpack')

# zmq variables
_ctx = zmq.Context()
_server = None
_email_producer = None  # emails

# datastore variables
_store = None
_schema = 'users'


# rpc api endpoints
rpc = rk.utils.RPC()


_sensitive = ('id', 'password', 'salt', 'reset_password')


def strip_sensitive(user, fields=_sensitive):
    [user.pop(key, None) for key in fields]
    return user


def handler(message):
    ibeg = rk.utils.time()
    sid, req = rk.utils.unpack(_proto, message)
    try:
        func = rpc[req.method]
        res = func(**req.args)
    except Exception as err:
        res = rk.utils.error(err)
        _log.exception(err)
    else:
        res['ok'] = True
    finally:
        _proto.send(_server, res, sid)
        iend = rk.utils.time()
        elapsed = 1000*(iend-ibeg)
        _log.info(f'{req.method} >> {func.__name__} {elapsed:0.2f}ms')


def _setup(server_addr, db_addr, email_addr):
    global _server, _store, _email_producer
    _server = rk.zkit.router(_ctx, server_addr, handler=handler)
    _email_producer = rk.zkit.producer(_ctx, email_addr)
    _store = sm.client.PGClient(db_addr)


def find_by_email(email):
    items = _store.filter(
        _schema, 'users', (('email',), (email,))
    )['items']
    try:
        return items[0]
    except IndexError:
        return None


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

    passed = _auth.request_verify_email(url, user['id'], user['email'])
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
def update_address(user_id, addr_id, street, city, postcode, country):
    data = {
        'street': street, 'city': city,
        'postcode': postcode, 'country': country
    }
    address = _store.update(_schema, 'address', addr_id, data)
    return address


@rpc.register('/users.address.list')
def list_address(user_id, limit=20, offset=0):
    params = (("user_id",), (user_id,))
    kwargs = {'offset': offset, 'limit': limit}
    addresses = _store.filter(
        _schema, 'address', params, **kwargs
    )
    return addresses


@rpc.register('/users.address.delete')
def delete_address(user_id, addr_id):
    _store.delete(_schema, 'address', addr_id)
    return {}


@rpc.register('/users.delete')
def delete_user(user_id):
    data = {'disabled': True}
    _store.update(_schema, 'users', user_id, data)
    return {}


@rpc.register('/users.auth.login')
def login_user(email, password):
    user = find_by_email(email)
    user = _auth.login(user, password)
    return strip_sensitive(user)


@rpc.register('/users.auth.requestVerifyEmail')
def request_verify_email(user_id):
    user = _store.get(_schema, 'users', user_id)
    data = _auth.request_verify_email(_url, user_id, user['email'])
    token = data.pop('token')
    _proto.send(_email_producer, data)
    return {'token': token}


@rpc.register('/users.auth.setEmailVerified')
def set_email_verified(token):
    data = _auth.verify_email(_store, token)
    return data


@rpc.register('/users.auth.requestPasswordReset')
def request_password_reset(email):
    user = find_by_email(email)
    data = _auth.request_password_reset(_url, _store, user['id'])
    token = data.pop('token')
    _proto.send(_email_producer, data)
    return {'token': token}


@rpc.register('/users.auth.setPassword')
def reset_password(token, password):
    passed = _auth.reset_password(_store, token, password)
    return {'passed': True}


def start(server_addr, db_addr, email_addr):
    _log.info('starting users service...')
    _setup(server_addr, db_addr, email_addr)
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('user service interrupted')
        _store.close()


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-s', '--server_addr', dest='server_addr',
        help='service end point',
        default='tcp://127.0.0.1:5000'
    )

    parser.add_argument(
        '-d', '--db_addr', dest='db_addr',
        help='database address',
        default='postgres://postgres:password@127.0.0.1:5433/users'
    )

    parser.add_argument(
        '-e', '--email_addr', dest='email_addr',
        help='email producer address',
        default='tcp://127.0.0.1:6001'
    )
    options = parser.parse_args()
    start(
        options.server_addr,
        options.db_addr,
        options.email_addr
    )


if __name__ == "__main__":
    main()
