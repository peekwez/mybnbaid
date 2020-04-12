import backless as bk

from . import users
from . import zones
from . import properties
from . import bookings
from . import cleans
from . import base


def factory(conf):
    # combine all handlers
    handlers = [
        (r'/logout', base.LogoutHandler, dict(rpc=None)),
        * users.handlers,
        *zones.handlers,
        *properties.handlers,
        *bookings.handlers,
        *cleans.handlers
    ]

    # get service configuration
    sas = bk.sas.AWSProvider(conf['credentials'], conf['stage'])
    sconf = sas.get_service_secret('gateway', conf['bucket'])

    # initialize asynchronous clients to service
    for _, handler, _ in handlers:  # url, handler, rpc
        try:
            service = handler._service

            # initialize asynchronous clients for rpc services
            if handler._rpc_client == None:
                handler._rpc_client = bk.rpc.AsyncRpcProxy(
                    conf['broker'], service, conf['verbose']
                )

            # initialize token authentication manager
            if handler._auth_manager == None:
                handler._auth_manager = bk.utils.AuthManager(
                    sconf['authentication']
                )

            # initialize repository for managing sessions
            if handler._repo == None:
                handler._repo = bk.repo.layers.SchemalessLayer(
                    'gateway', sconf['repository']
                )
        except AttributeError:
            pass

    return handlers


def cleanup(handlers):
    # close connections to repository
    for _, handler, _ in handlers:
        if handler._repo is not None:
            handler._repo.close()
            handler._repo = None


__all__ = ['factory', 'cleanup']
