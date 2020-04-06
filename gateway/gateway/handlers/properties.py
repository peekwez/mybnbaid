from . import base


class PropertiesHandler(base.BaseHandler):
    _service = 'properties'


handlers = [
    (r'/properties.info', PropertiesHandler, dict(rpc='info', auth=False)),
]
