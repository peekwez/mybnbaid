ROOT = (
    "Make",
    "Makefile",
    "MANIFEST",
    "run",
    "setup",
    "docker"
)

EXTS = (
    "in",
    "",
    "in",
    "sh",
    "py",
    "run"
)


PROJECT = (
    "__init__.py",
    "service.py",
    "exceptions.py"
)


def create_files(rootdir, service):
    import os

    _one = f'{rootdir}/{service}'
    _two = f'{rootdir}/{service}/{service}'
    samples = f'{rootdir}/sample'
    _env = Environment(
        loader=FileSystemLoader(samples)
    )
    context = {'service': service}

    # create level 1 files
    if not os.path.exists(_one):
        os.makedirs(_one)
        for k, file in enumerate(ROOT):
            filename = f'{file}.txt'
            template = _env[filename]
            rendered = template.render(context)
            newfile = f'{level_one}/{file}.{EXTS[k]}'
            with open(newfile, 'wb') as f:
                f.write(rendered)

    # create level 3 files
    if not os.path.exists(_two):
        os.makedirs(_two)
        for file in PROJECT:
            filename = f'{_two}/{file}
            with open(filename, 'w') as f:
                pass


def main():
    from jinja2 import Environment, FileSystemLoader

    from argparse import ArgumentParser
    parser = ArgumentParser()

    parser.add_argument(
        '-d', '--rootdir', dest='rootdir'
        help='project root directory'
    )
    parser.add_argument(
        '-s', '--service', dest='service',
        help='microservice name',
    )

    options = parser.parse_args()
    create_files(options.rootdir, options.service)


if __name__ == "__main__":
    main()
