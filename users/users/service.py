import backless as bk

from . import exceptions as exc


class UsersService(bk.iam.service.IAMService):
    _name = "users"
    _schema = "users"
    _version = "0.0.1"
    _url = "https://mybnbaid.com"


def main():
    bk.utils.start_service(UsersService)


if __name__ == "__main__":
    main()
