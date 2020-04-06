from . import base


class CleansHandler(base.BaseHandler):
    _service = 'cleans'


handlers = [
    (r'/cleans.info', CleansHandler, dict(rpc='info', auth=False)),
]
