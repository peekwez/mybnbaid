import backless as bk


class MailService(bk.mail.service.MailService):
    _name = "mail"
    _version = "0.0.1"


def main():
    bk.utils.start_service(MailService)


if __name__ == "__main__":
    main()
