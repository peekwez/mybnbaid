import os
import zmq
from zmq.eventloop.future import Context

import tornado
from tornado import ioloop
from tornado import gen
from tornado import web
from tornado.log import enable_pretty_logging

import rock as rk

from . import exceptions as exc


_token = None
_services = None

enable_pretty_logging()


def _setup(services):
    global _token, _services
    s = {"LOGIN": rk.aws.get_token_secrets()['LOGIN']}
    _token = rk.auth.TokenManager(s)
    _services = services


def get_header(request):
    try:
        header = request.headers["Authorization"]
    except KeyError:
        raise exc.MissingHeader('authorization header missing')
    return header


def get_token(header):
    try:
        token = header.split('Bearer')[1].strip()
    except IndexError:
        raise exc.BadHeaderFormat(
            'authorization header format incorrect'
        )
    return token


def get_data(request):
    data = {}
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            data = rk.msg.loads(request.body)
        except rk.msg.json.decoder.JSONDecodeError:
            data = {}
    return data


def authenticate(request):
    header = get_header(request)  # check for header
    token = get_token(header)  # get token
    user_id = _token.verify('LOGIN', token, ttl=10000)  # verify token


class GatewayHandler(web.RequestHandler):
    _msg = rk.msg.Client(b'mpack')
    _auth = False

    def initialize(self):
        self._addr = _services[self._svc]

    def reply_error(self, err):
        res = rk.utils.error(err)
        self.write(rk.msg.dumps(res))
        self.set_header('Content-Type', 'application/json')
        self.finish()

    def prepare(self):
        self.data = get_data(self.request)
        if self._auth == True:
            try:
                user_id = self.current_user
            except Exception as err:
                self.reply_error(err)
            else:
                self.data.update({'user_id': user_id})

    @property
    def uri(self):
        return self.request.uri

    @gen.coroutine
    def post(self):
        req = rk.utils.prep(method=self.uri, args=self.data)
        ctx = Context()
        sock = ctx.socket(zmq.DEALER)
        sock.connect(self._addr)

        yield self._msg.send(sock, req)
        reply = yield sock.recv()
        res = self._msg.unpack(reply)

        sock.close()
        ctx.term()

        if reply:
            yield self.write(rk.msg.dumps(res))
            yield self.set_header(
                'Content-Type', 'application/json'
            )


class AuthGatewayHandler(GatewayHandler):
    _auth = True

    def get_current_user(self):
        user_id = authenticate(self.request)
        return user_id


class UsersNoAuthHandler(GatewayHandler):
    _svc = 'users'


class UsersHandler(AuthGatewayHandler):
    _svc = 'users'


class ZonesHandler(AuthGatewayHandler):
    _svc = 'zones'


# class AccountsHandler(AuthGatewayHandler):
#     _svc = 'accounts'


# class BookingsHandler(AuthGatewayHandler):
#     _svc = 'bookings'


# class CleansHandler(AuthGatewayHandler):
#     _svc = 'cleans'


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-p', '--port', dest='port',
        help='port to listen on', default=8888
    )
    parser.add_argument(
        '-c', '--config', dest='config',
        help='configuration with service available',
        default='config.yml'
    )
    opts = parser.parse_args()

    handlers = [
        (r'/users.create', UsersNoAuthHandler),
        (r'/users.auth.login', UsersNoAuthHandler),
        (r'/users.auth.setEmailVerified', UsersNoAuthHandler),
        (r'/users.auth.requestPasswordReset', UsersNoAuthHandler),
        (r'/users.auth.setPassword', UsersNoAuthHandler),
        (r'/users.auth.requestVerifyEmail', UsersHandler),
        (r'/users.setName', UsersHandler),
        (r'/users.setPhoneNumber', UsersHandler),
        (r'/users.address.create', UsersHandler),
        (r'/users.address.update', UsersHandler),
        (r'/users.address.list', UsersHandler),
        (r'/users.address.delete', UsersHandler),
        (r'/zones.getArea', ZonesHandler),
        (r'/zones.getCity', ZonesHandler),
        (r'/zones.getRegion', ZonesHandler),
        (r'/zones.areas', ZonesHandler),
        (r'/zones.cities', ZonesHandler),
        (r'/zones.regions', ZonesHandler),
    ]

    app = web.Application(handlers)
    app.listen(opts.port)
    try:
        cfg = rk.utils.handle_config(opts.config, 'gateway')
        _setup(cfg['services'])
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted')


if __name__ == "__main__":
    main()
