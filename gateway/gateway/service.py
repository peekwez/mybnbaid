import tornado
import signal
from tornado import ioloop
from tornado import web
from tornado.log import enable_pretty_logging

import rock as rk
from . import handlers as hd


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
        help='configuration with services available',
        default='config.yml'
    )
    # parse command line
    opts = parser.parse_args()

    # read config file
    conf = rk.utils.read_config(opts.config)

    # get handlers
    handlers = hd.factory(conf)

    # register function to cleanup after sig termination
    def cleanup(*args, **kwargs): return hd.cleanup(handlers)
    signal.signal(signal.SIGTERM, cleanup)

    # initialize and run app
    app = web.Application(handlers)
    app.listen(opts.port)
    try:
        ioloop.IOLoop.current().start()
    except:
        print('Interrupted...')
    finally:
        cleanup()


if __name__ == "__main__":
    main()
