
from tornado import gen
from tornado import web
from tornado.concurrent import run_on_executor
from concurrent.futures import ThreadPoolExecutor

import rock as rk

from . import mapping

_token = rk.auth.TokenManager(
    {'LOGIN': rk.aws.get_token_secrets()['LOGIN']}
)
MAX_WORKERS = 4


def get_data(request):
    data = {}
    if request.headers.get('Content-Type', '').startswith('application/json'):
        try:
            data = rk.msg.loads(request.body)
        except rk.msg.json.decoder.JSONDecodeError:
            data = {}
    return data


class BaseHandler(web.RequestHandler):
    executor = ThreadPoolExecutor(
        max_workers=MAX_WORKERS
    )
    _map = mapping.urls
    _client = None
    _name = None

    def prepare(self):
        self.data = get_data(self.request)

    @property
    def uri(self):
        return self.request.uri

    @run_on_executor
    def process_request(self):
        method = self._map.get(self.uri)
        message = rk.msg.pack(method, self.data)
        self._client.send(self._name, message)
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
        return rk.msg.munpack(reply[-1])

    @gen.coroutine
    def post(self):
        reply = yield self.process_request()
        if reply:
            yield self._on_complete(reply)

    def _on_complete(self, res):
        self.write(rk.msg.dumps(res))
        self.set_header('Content-Type', 'application/json')
        self.finish()


class BaseAuthHandler(BaseHandler):
    def prepare(self):
        super(BaseAuthHandler, self).prepare()
        token = self.data.pop('token')
        if not token:
            self._on_complete({
                "ok": True,
                "error": 'MissingToken',
                'details': 'request token was not provided'
            })
        try:
            user_id = _token.verify(token)
        except Exception as err:
            self._on_complete(rk.utils.error(err))
