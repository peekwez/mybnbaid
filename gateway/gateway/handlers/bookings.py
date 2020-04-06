from . import base


class BookingsHandler(base.BaseHandler):
    _service = 'bookings'


handlers = [
    (r'/bookings.info', BookingsHandler, dict(rpc='info', auth=False)),
]
