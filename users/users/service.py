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
_producers = {}

# datastore variables
_schema = 'users'
_store = None


# rpc api endpoints
rpc = rk.utils.RPC()

# fields to remove before sending
_sensitive = ('id', 'password', 'salt', 'reset_password')


def strip_sensitive(user, fields=_sensitive):
    [user.pop(key, None) for key in fields]
    return user


def handler(message):
    rk.utils.handle_rpc(message, rpc, _proto, _server, _log)


def _setup(cfg):
    global _server, _producers, _store
    _server = rk.zkit.router(_ctx, cfg['addr'], handler=handler)
    prods = cfg.get('producers', None)
    if prods:
        for key in prods:
            _producers[key] = rk.zkit.producer(_ctx, prods[key])
    _store = sm.client.PGClient(rk.aws.get_db_secret('users'))
    _log.info('users service, producers and datstore started...')


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

    data = _auth.request_welcome_email(_url, user['id'], user['email'])
    token = data.pop('token')
    _proto.send(_producers['mail'], data)
    user['verify_token'] = token
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
    text = {
        'action': 'send',
        'message': 'Welcome to mybnbaid!',
        'number': 'phone_number'
    }
    _proto.send(_producers['sms'], text)
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
    if not user:
        raise exc.UserNotFound('user does not exist')
    user = _auth.login(user, password)
    return strip_sensitive(user)


@rpc.register('/users.auth.requestVerifyEmail')
def request_verify_email(user_id):
    user = _store.get(_schema, 'users', user_id)
    data = _auth.request_verify_email(_url, user_id, user['email'])
    token = data.pop('token')
    _proto.send(producers['mail'], data)
    return {'token': token}


@rpc.register('/users.auth.setEmailVerified')
def set_email_verified(token):
    data = _auth.verify_email(_store, token)
    return data


@rpc.register('/users.auth.requestPasswordReset')
def request_password_reset(email):
    user = find_by_email(email)
    if not user:
        raise exc.UserNotFound('user does not exist')
    data = _auth.request_password_reset(_url, _store, user['id'])
    token = data.pop('token')
    _proto.send(producers['mail'], data)
    return {'token': token}


@rpc.register('/users.auth.setPassword')
def reset_password(token, password):
    passed = _auth.reset_password(_store, token, password)
    return {'passed': True}


def main():
    cfg = rk.utils.parse_config('services')
    _log.info('starting users service...')
    _setup(cfg['users'])
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('user service interrupted')
    finally:
        _store.close()


if __name__ == "__main__":
    main()
