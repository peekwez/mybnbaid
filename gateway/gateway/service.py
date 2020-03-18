import tornado
from tornado import ioloop
from tornado import web
from tornado.log import enable_pretty_logging

from .handlers.users import UsersHandler, UsersNoAuthHandler

enable_pretty_logging()


def main():
    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-p', '--port', dest='port',
        help='port to listen on', default=8888
    )
    parser.add_argument(
        '-c', '--config', dest='config',
        help='configuration with service available',
        default='config.yml'
    )
    opts = parser.parse_args()

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
        (r'/users.address.list', UsersHandler)
        # (r'/users.address.delete', UsersHandler),
        # (r'/zones.getArea', ZonesHandler),
        # (r'/zones.getCity', ZonesHandler),
        # (r'/zones.getRegion', ZonesHandler),
        # (r'/zones.areas', ZonesHandler),
        # (r'/zones.cities', ZonesHandler),
        # (r'/zones.regions', ZonesHandler),
    ]

    app = web.Application(handlers)
    app.listen(opts.port)
    try:
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted')


if __name__ == "__main__":
    main()
