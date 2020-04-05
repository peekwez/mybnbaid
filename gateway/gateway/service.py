import tornado
from tornado import ioloop
from tornado import web
from tornado.log import enable_pretty_logging

import rock as rk

from .handlers import clients as hd


enable_pretty_logging()


def initialize(conf, handlers):
    # inject asynchronous RpcProxy and auth for services
    _sas = rk.sas.AWSProvider(conf['credentials'], conf['stage'])
    _conf = _sas.get_service_secret('gateway', conf['bucket'])
    for _, handler in handlers:
        try:
            service = handler._service
            if handler._rpc_client == None:
                # inject service clients
                handler._rpc_client = rk.rpc.AsyncRpcProxy(
                    conf['broker'], handler._service, conf['verbose']
                )

                # check for auth and start manager
                if hasattr(handler, '_auth'):
                    handler._auth = rk.utils.AuthManager(
                        _conf['authentication']
                    )
        except AttributeError:
            pass


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-p', '--port', dest='port',
        help='port to listen on', default=8888
    )
    parser.add_argument(
        '-c', '--config', dest='config',
        help='configuration with services available',
        default='config.yml'
    )
    opts = parser.parse_args()
    conf = rk.utils.read_config(opts.config)

    handlers = [
        (r'/users.info', hd.UsersNoAuthHandler),
        (r'/users.create', hd.UsersNoAuthHandler),
        (r'/users.auth.login', hd.UsersNoAuthHandler),
        (r'/users.auth.setEmailVerified', hd.UsersNoAuthHandler),
        (r'/users.auth.requestPasswordReset', hd.UsersNoAuthHandler),
        (r'/users.auth.setPassword', hd.UsersNoAuthHandler),
        (r'/users.auth.requestVerifyEmail', hd.UsersHandler),
        (r'/users.setName', hd.UsersHandler),
        (r'/users.setPhoneNumber', hd.UsersHandler),
        (r'/users.address.create', hd.UsersHandler),
        (r'/users.address.update', hd.UsersHandler),
        (r'/users.address.list', hd.UsersHandler),
        (r'/users.address.delete', hd.UsersHandler),
        (r'/zones.info', hd.ZonesNoAuthHandler),
        (r'/zones.getLocation', hd.ZonesHandler),
        (r'/zones.getCity', hd.ZonesHandler),
        (r'/zones.getRegion', hd.ZonesHandler),
        (r'/zones.locations', hd.ZonesHandler),
        (r'/zones.cities', hd.ZonesHandler),
        (r'/zones.regions', hd.ZonesHandler),
        (r'/properties.info', hd.PropertiesNoAuthHandler),
        (r'/bookings.info', hd.BookingsNoAuthHandler),
        (r'/cleans.info', hd.CleansNoAuthHandler),
    ]

    # initialize clients
    initialize(conf, handlers)

    # initialize and run app
    app = web.Application(handlers)
    app.listen(opts.port)
    try:
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted')


if __name__ == "__main__":
    main()
