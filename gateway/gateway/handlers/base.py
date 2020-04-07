import json

from tornado import gen, web, log
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

import rock as rk

MAX_WORKERS = 4
CONTENT_TYPE = 'application/json'


class LoginRequired(Exception):
    pass


class TokenRequired(Exception):
    pass


class BaseHandler(web.RequestHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    _service = None
    _repo = None
    _rpc_client = None
    _auth_manager = None

    def initialize(self, rpc, auth=True, init_session=False):
        self._rpc = rpc
        self._auth = auth
        self._init_session = init_session
        self._token = None

    def prepare(self):
        try:
            self._get_data()
            if self._auth:
                self._authenticate()
        except Exception as err:
            self._on_complete(rk.utils.error(err))

    @gen.coroutine
    def post(self):
        reply = yield self._process_request()
        if reply:
            yield self._on_complete(reply)

    @run_on_executor
    def _process_request(self):
        rpc_method = getattr(self._rpc_client, self._rpc)
        reply = rpc_method(**self.args)
        if (reply and self._init_session):
            if reply['ok'] == True:
                self._start_session(reply['token'])
        return reply

    def _get_data(self):
        self.args = dict()
        content_type = self.request.headers.get('Content-Type', '')
        if content_type.startswith(CONTENT_TYPE):
            self.args = json.loads(self.request.body)

    def _start_session(self, token):
        self._repo.cache.set(
            token, '1', noreply=True, expire=28800
        )

    def _session_is_active(self, token):
        return self._repo.cache.get(token) == '1'

    def _verify_token(self, token):
        return self._auth_manager.verify_token(
            'login-user', token, ttl=28800
        )

    def _get_token(self):
        try:
            token = self.args.pop('token')
        except KeyError:
            raise TokenRequired('request token not provided')
        else:
            return token

    def _authenticate(self):
        token = self._get_token()

        if not self._session_is_active(token):
            raise LoginRequired('user is not logged in')

        user_id = self._verify_token(token)
        self.args.update(dict(user_id=user_id))
        self._token = token

    def _on_complete(self, res):
        self.write(json.dumps(res))
        self.set_header('Content-Type', CONTENT_TYPE)
        self.finish()
        return


class LogoutHandler(BaseHandler):
    _service = 'gateway'
    _rpc_client = 'gateway'

    @gen.coroutine
    def post(self):
        reply = self._repo.cache.delete(self._token)
        if reply:
            yield self._on_complete(dict(ok=True))
