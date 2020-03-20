import json

from tornado import gen
from tornado import web
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

import rock as rk

from . import mapping


MAX_WORKERS = 4


class BaseHandler(web.RequestHandler):
    executor = ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    )
    _map = mapping.urls
    _client = None
    _service = None

    def prepare(self):
        self.data = {}
        content_type = self.request.headers.get('Content-Type', '')
        if content_type.startswith('application/json'):
            try:
                self.data = json.loads(self.request.body)
            except json.decoder.JSONDecodeError:
                self._on_complete(rk.utils.error(err))

    @property
    def uri(self):
        return self.request.uri

    @run_on_executor
    def process_request(self):
        method = self._map[self.uri]
        message = rk.msg.prepare(method, self.data)
        self._client.send(self._service, message)
        response = False
        while not response:
            try:
                reply = self._client.recv()
            except KeyboardInterrupt:
                break
            else:
                if reply is None:
                    break
                response = True
        return rk.msg.unpack(reply[-1])

    @gen.coroutine
    def post(self):
        reply = yield self.process_request()
        if reply:
            yield self._on_complete(reply)

    def _on_complete(self, res):
        self.write(json.dumps(res))
        self.set_header('Content-Type', 'application/json')
        self.finish()
        return


class BaseAuthHandler(BaseHandler):
    _token = rk.auth.TokenManager(
        {'LOGIN': rk.aws.get_token_secrets()['LOGIN']}
    )

    def prepare(self):
        super(BaseAuthHandler, self).prepare()
        try:
            token = self.data.pop('token')
        except KeyError:
            self._on_complete({
                "ok": True,
                "error": 'MissingToken',
                'details': 'request token is missing'
            })
        try:
            user_id = self._token.verify('LOGIN', token, ttl=28800)
            self.data.update({'user_id': user_id})
        except Exception as err:
            self._on_complete(rk.utils.error(err))
