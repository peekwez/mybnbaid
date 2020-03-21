import zmq
import collections
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop
from multiprocessing import Process, Pool


import rock as rk

MailParser = collections.namedtuple(
    'MailParser', ('subject', 'emails', 'html', 'text')
)
MAX_WORKERS = 4


def consumer(addr):
    log = rk.utils.logger('mail.service')
    ses = rk.aws.get_client(
        'ses', use_session=False,
        region='us-east-1'
    )

    def section(name, value):
        return {name.title(): {
            'Data': value,
            'Charset': 'UTF-8'}}

    def handler(message):
        mail = MailParser(**rk.msg.unpack(message[-1]))
        try:
            contents = {
                **section('subject', mail.subject),
                'Body': {
                    **section('text', mail.text),
                    **section('html', mail.html)
                }
            }
            response = ses.send_email(
                Source='no-reply@mybnbaid.com',
                Destination={'ToAddresses': mail.emails},
                Message=contents
            )
        except Exception as err:
            log.exception(err)
            result = 'failed...'
        else:
            metadata = response.get("ResponseMetadata")
            if metadata.get('HTTPStatusCode') == 200:
                result = 'sent...'
        finally:
            log.info(f'{mail.subject} to {mail.emails} {result}')

    ctx, sock = rk.zkit.consumer(addr, handler)
    log.info('consumer started...')

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('consumer interrupted...')
    finally:
        log.info('closing consumer socket...')
        sock.close()
        if ctx:
            ctx.term()


class MailService(rk.utils.BaseService):
    _name = b'mail'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(MailService, self).__init__(brokers, conf, verbose)
        self._setup_ipc()

        self._ctx, self._producer = rk.zkit.producer(self._ipc)
        self._log.info('mail producer started...')

        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (
                Process(target=consumer, args=(self._ipc,)),
            )

    def send(self, emails, subject, html, text):
        mail = rk.msg.pack(
            dict(
                emails=emails,
                subject=subject,
                html=html,
                text=text
            )
        )
        self._producer.send(mail)
        return {
            'ok': True,
            'details': 'email submitted for processing'
        }


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['mail']
    with MailService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
