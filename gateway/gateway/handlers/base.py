import json

from tornado import gen
from tornado import web
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

import rock as rk

from . import mapping

MAX_WORKERS = 4


class BaseHandler(web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    _rpc_client = None
    _service = None
    _auth_manager = None

    def initialize(self, rpc, auth=True):
        self._rpc = rpc
        self._auth = auth

    def prepare(self):
        self._get_data()
        if self._auth:
            self._authenticate()

    @gen.coroutine
    def post(self):
        reply = yield self._process_request()
        if reply:
            yield self._on_complete(reply)

    @run_on_executor
    def _process_request(self):
        rpc_method = getattr(self._rpc_client, self._rpc)
        return rpc_method(**self.data)

    def _get_data(self):
        self.data = dict()
        content_type = self.request.headers.get('Content-Type', '')
        if content_type.startswith('application/json'):
            try:
                self.data = json.loads(self.request.body)
            except json.decoder.JSONDecodeError:
                self._on_complete(rk.utils.error(err))

    def _authenticate(self):
        try:
            token = self.data.pop('token')
        except KeyError:
            error = dict(
                ok=False, error='MissingToken',
                details='request token missing'
            )
            self._on_complete(error)

        try:
            user_id = self._auth_manager.verify_token(
                'login-user', token, ttl=28800
            )
            self.data.update({'user_id': user_id})
        except Exception as err:
            self._on_complete(rk.utils.error(err))

    def _on_complete(self, res):
        self.write(json.dumps(res))
        self.set_header('Content-Type', 'application/json')
        self.finish()
        return
