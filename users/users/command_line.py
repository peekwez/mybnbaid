import users


def addparser():

    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-ip', '--addr', dest='addr',
        help='service end point',
        default='tcp://127.0.0.1:5000'
    )

    parser.add_argument(
        '-dsn', '--dsn', dest='dsn',
        help='database address',
        default='postgres://postgres:password@127.0.0.1:5433/schemaless'
    )
    return parser


def main():
        # parse arguments
    parser = addparser()
    options = parser.parse_args()

    # run appropriate command
    users.service.start(options.addr, options.dsn)


if __name__ == "__main__":
    main()
