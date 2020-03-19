import os
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

    ctx = zmq.Context(1)
    sock = ctx.socket(zmq.PULL)
    sock.connect(addr)
    sock.linger = 0
    sock = ZMQStream(sock)
    sock.on_recv(handler)
    log.info('mail consumer started...')

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('consumer interrupted...')
    finally:
        log.info('consumer ending gracefully...')
        sock.close()
        ctx.term()


def producer(addr):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.bind(addr)
    return ctx, sock


class MailService(rk.utils.BaseService):
    __slots__ = ('_ctx', '_unix', '_addr', '_producer', '_consumers')
    _name = b'mail'
    _version = b'0.0.1'
    _log = rk.utils.logger('mail.service')

    def __init__(self, brokers, conf, verbose):
        super(MailService, self).__init__(brokers, conf, verbose)
        self._unix = f'/tmp/mail.{os.getpid()}.sock'
        self._addr = f'ipc://{self._unix}'
        self._ctx, self._producer = producer(self._addr)
        self._log.info('mail producer started...')
        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (Process(target=consumer, args=(self._addr,)),)

    def __exit__(self, type, value, traceback):
        super(MailService, self).__exit__(type, value, traceback)
        self._producer.close()
        self._ctx.term()
        for worker in self._consumers:
            worker.terminate()
        if os.path.exists(self._unix):
            os.remove(self._unix)
            self.log.info(f'{self._unix} removed...')

    def __call__(self):
        for worker in self._consumers:
            worker.start()
        super(MailService, self).__call__()

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
