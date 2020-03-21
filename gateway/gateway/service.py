import tornado
from tornado import ioloop
from tornado import web
from tornado.log import enable_pretty_logging

import rock as rk

from .handlers.clients import (
    UsersHandler, UsersNoAuthHandler,
    ZonesHandler
)

enable_pretty_logging()


def init(brokers, handlers, verbose):
    # inject asynchronous major domo into class handlers
    for _, handler in handlers:
        try:
            service = handler._service.decode('utf-8')
            if handler._client == None:
                handler._client = rk.mdp.aclient.MajorDomoClient(
                    brokers[service], handler._service, verbose
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
        default='services.yml'
    )
    opts = parser.parse_args()
    conf = rk.utils.read_config(opts.config)

    handlers = [
        (r'/users.create', UsersNoAuthHandler),
        (r'/users.auth.login', UsersNoAuthHandler),
        (r'/users.auth.setEmailVerified', UsersNoAuthHandler),
        (r'/users.auth.requestPasswordReset', UsersNoAuthHandler),
        (r'/users.auth.setPassword', UsersNoAuthHandler),
        (r'/users.auth.requestVerifyEmail', UsersHandler),
        (r'/users.setName', UsersHandler),
        (r'/users.setPhoneNumber', UsersHandler),
        (r'/users.address.create', UsersHandler),
        (r'/users.address.update', UsersHandler),
        (r'/users.address.list', UsersHandler),
        (r'/users.address.delete', UsersHandler),
        (r'/zones.getLocation', ZonesHandler),
        (r'/zones.getCity', ZonesHandler),
        (r'/zones.getRegion', ZonesHandler),
        (r'/zones.locations', ZonesHandler),
        (r'/zones.cities', ZonesHandler),
        (r'/zones.regions', ZonesHandler)
    ]

    # initialize clients
    init(conf['brokers'], handlers, conf.get('verbose') == True)

    # initialize and run app
    app = web.Application(handlers)
    app.listen(opts.port)
    try:
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted')


if __name__ == "__main__":
    main()
