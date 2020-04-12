import backless as bk


class SMSService(bk.sms.service.SMSService):
    _name = "sms"
    _version = "0.0.1"


def main():
    bk.utils.start_service(SMSService)


if __name__ == "__main__":
    main()
