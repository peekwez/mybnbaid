import rock as rk

from . import users
from . import zones
from . import properties
from . import bookings
from . import cleans


def get_auth_config(conf):
    _sas = rk.sas.AWSProvider(conf['credentials'], conf['stage'])
    _conf = _sas.get_service_secret('gateway', conf['bucket'])
    return _conf['authentication']


def factory(conf):
    # combine all handlers
    handlers = [
        *users.handlers,
        *zones.handlers,
        *properties.handlers,
        *bookings.handlers,
        *cleans.handlers
    ]

    # get authentication configuration
    auth_conf = get_auth_config(conf)

    # initialize asynchronous clients to service
    for _, handler, _ in handlers:
        try:
            service = handler._service
            if handler._rpc_client == None:
                handler._rpc_client = rk.rpc.AsyncRpcProxy(
                    conf['broker'], handler._service, conf['verbose']
                )

            if handler._auth_manager == None:
                handler._auth_manager = rk.utils.AuthManager(auth_conf)
        except AttributeError:
            pass

    return handlers


__all__ = ['factory']
