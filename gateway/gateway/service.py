import os
import zmq
from zmq.eventloop.future import Context

import tornado
from tornado import ioloop
from tornado import gen
from tornado import web
from tornado.options import define, options
from tornado.log import enable_pretty_logging

import rock as rk

from . import exceptions as exc


_token = None


def start_token_manager():
    global _token
    prod = os.environ.get('MYBNBAID-PROD', False)
    name = 'DEV_TOKEN_SECRETS'
    if prod:
        name = 'PROD_TOKEN_SECRETES'
    s = {'LOGIN': rk.aws.get_secret(name)['LOGIN']}
    _token = rk.auth.TokenManager(s)


def get_header(r):
    try:
        header = r.headers["Authorization"]
    except KeyError:
        raise exc.MissingHeader('authorization header missing')
    return header


def get_token(h):
    try:
        token = h.split('Bearer')[1].strip()
    except IndexError:
        raise exc.BadHeaderFormat(
            'authorization header format incorrect'
        )
    return token


class GatewayHandler(web.RequestHandler):
    _addr = None
    _msg = rk.msg.Client(b'mpack')
    data = None

    def initialize(self, auth=False):
        self._auth = auth

    def reply_error(self, err):
        res = rk.utils.error(err)
        self.write(rk.msg.dumps(res))
        self.set_header('Content-Type', 'application/json')
        self.finish()

    def prepare(self):

        if self.request.headers.get('Content-Type', '').startswith('application/json'):
            try:
                self.data = rk.msg.loads(self.request.body)
            except rk.msg.json.decoder.JSONDecodeError:
                self.data = {}

        if self._auth == True:

            # is header present
            try:
                header = get_header(self.request)
            except Exception as err:
                self.reply_error(err)

            # is token in proper format
            try:
                token = get_token(header)
            except Exception as err:
                self.reply_error(err)

            # is token valid
            try:
                user_id = _token.verify('LOGIN', token, ttl=10000)
                self.data.update({'user_id': user_id})
            except Exception as err:
                self.reply_error(err)

            # is user logged in :: session

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


class UserHandler(GatewayHandler):
    _addr = 'tcp://127.0.0.1:5001'


enable_pretty_logging()
define('port', default=8888, help='port to listen')


def main():
    handlers = [
        (r'/users.create', UserHandler),
        (r'/users.setName', UserHandler, dict(auth=True)),
        (r'/users.setPhoneNumber', UserHandler, dict(auth=True)),
        (r'/users.address.create', UserHandler, dict(auth=True)),
        (r'/users.address.update', UserHandler, dict(auth=True)),
        (r'/users.address.list', UserHandler, dict(auth=True)),
        (r'/users.address.delete', UserHandler, dict(auth=True)),
        (r'/users.auth.login', UserHandler),
        (r'/users.auth.requestVerifyEmail', UserHandler, dict(auth=True)),
        (r'/users.auth.setEmailVerified', UserHandler),  # body has token
        (r'/users.auth.requestPasswordReset', UserHandler),
        (r'/users.auth.setPassword', UserHandler)  # body has token
    ]
    app = web.Application(handlers)
    app.listen(options.port)
    try:
        start_token_manager()
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted')


if __name__ == "__main__":
    tornado.options.parse_command_line()
    main()
