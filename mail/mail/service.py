import os
import zmq
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop
from multiprocessing import Process


import rock as rk


def section(name, value):
    return {
        name.title: {
            'Data': value,
            'Charset': 'UTF-8'
        }
    }


def consumer(addr):
    log = rk.utils.logger('mail.service')
    ses = rk.aws.get_client(
        'ses', use_session=False,
        region='us-east-1'
    )

    def send_mail(message):
        req = rk.msg.unpack(message[-1])
        try:
            contents = {
                **section('subject', req.subject),
                'Body': {
                    **section('text', req.text),
                    **section('html', req.html)
                }
            }
            response = ses.send_email(
                Source='no-reply@mybnbaid.com',
                Destination={'ToAddresses': req.emails},
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
            log.info(f'{req.subject} email to {req.emails} {result}')

    ctx = zmq.Context()
    sock = ctx.socket(zmq.PULL)
    sock.bind(addr)
    sock.linger = 0
    sock = ZMQStream(sock)
    sock.on_recv(send_mail)
    log.info('mail consumer started...')

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('consumer interrupted')
    finally:
        sock.close()
        ctx.term()


def producer(addr):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.connect(addr)
    return ctx, sock


class MailService(rk.utils.BaseService):
    __slots__ = ('_ctx', '_unix', '_addr', '_producer')
    _name = b'mail'
    _version = b'0.0.1'
    _log = rk.utils.logger('mail.service')

    def __init__(self, brokers, conf, verbose):
        super(MailService, self).__init__(brokers, conf, verbose)
        self._unix = f'/tmp/mail.{os.getpid()}.sock'
        self._addr = f'ipc://{self._unix}'
        self._ctx, self._producer = producer(self._addr)
        self._log.info('mail producer started...')

    def __exit__(self, type, value, traceback):
        super(MailService, self).__exit__(type, value, traceback)
        self._producer.close()
        self._ctx.term()
        if os.path.exists(self._unix):
            os.remove(self._unix)

    def send(self, message):
        self._producer.send(message)
        return {
            'ok': True,
            'details': 'email submitted for processing'
        }


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['mail']
    with MailService(brokers, conf, verbose) as service:
        worker = Process(target=consumer, args=(service._addr,))
        worker.start()
        service()


if __name__ == "__main__":
    main()
