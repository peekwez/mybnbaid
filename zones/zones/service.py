import zmq

from tornado import ioloop

import rock as rk

from . import exceptions as exc
from . import store as db

# logging variables
_log = rk.utils.logger('zones.service', 'INFO')

# message format
_proto = rk.msg.Client(b'mpack')

# zmq variables
_ctx = zmq.Context()
_server = None

# zone data
_store = None

# rpc api endpoints
rpc = rk.utils.RPC()


def handler(message):
    rk.utils.handle_rpc(message, rpc, _proto, _server, _log)


def _setup(cfg):
    global _server, _store
    _server = rk.zkit.router(_ctx, cfg['addr'], handler=handler)
    _store = db.ZoneStore()
    _log.info('zones service and datstore started...')


@rpc.register('/zones.getArea')
def get_location(fsa):
    return _store.zones.location(fsa)


@rpc.register('/zones.getCity')
def get_city(fsa):
    return _store.zones.city(fsa)


@rpc.register('/zones.getRegion')
def get_region(fsa):
    return _store.zones.region(fsa)


@rpc.register('/zones.areas')
def get_location():
    return _store.zones.areas()


@rpc.register('/zones.cities')
def get_city(fsa):
    return _store.zones.cities(fsa)


@rpc.register('/zones.regions')
def get_region(fsa):
    return _store.zones.regions(fsa)


def main():
    cfg = rk.utils.parse_config('services')
    _log.info('starting zones service...')
    _setup(cfg['zones'])
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('zones service interrupted')
    finally:
        _store.close()


if __name__ == "__main__":
    main()
