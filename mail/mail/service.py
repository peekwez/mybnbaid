import collections

import rock as rk

MailParser = collections.namedtuple(
    'MailParser', ('subject', 'emails', 'html', 'text')
)
MAX_WORKERS = 4


def section(name, value):
    return {name.title(): {'Data': value, 'Charset': 'UTF-8'}}


class MailConsumer(rk.utils.BaseConsumer):
    def __init__(self, addr, name):
        super(MailConsumer, self).__init__(addr, name)
        self._ses = rk.aws.get_client(
            'ses', use_session=False, region='us-east-1'
        )

    def __prep(self, subject, html, text):
        body = {
            **section('subject', subject),
            'Body': {
                **section('text', text),
                **section('html', html)
            }
        }
        return body

    def send(self, data):
        opts = MailParser(**data)
        body = self.__prep(opts.subject, opts.html, opts.text)
        response = self._ses.send_email(
            Source='no-reply@mybnbaid.com',
            Destination={'ToAddresses': opts.emails},
            Message=body
        )
        return rk.aws.parse_response(response)


class MailService(rk.utils.BaseService):
    _name = b'mail'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(MailService, self).__init__(brokers, conf, verbose)
        self._setup_events(MailConsumer, MAX_WORKERS)

    def send(self, emails, subject, html, text):
        data = dict(
            emails=emails, subject=subject, html=html, text=text
        )
        return self._emit('send', data)


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['mail']
    with MailService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
