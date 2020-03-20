import zmq
import collections
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop
from multiprocessing import Process, Pool

import rock as rk

SMSParser = collections.namedtuple(
    'SMSParser', ('action', 'topic', 'number', 'message')
)
MAX_WORKERS = 4


def consumer(addr):
    log = rk.utils.logger('sms.service')
    sns = rk.aws.get_client(
        'sns', use_session=False, region='us-east-1'
    )
    topics = collections.OrderedDict()
    groups = sns.list_topics()['Topics']
    if groups:
        for topic in groups:
            arn = topic['TopicArn']
            name = arn.split(':')[-1]
            topics[name] = arn

    def send(number, message):
        response = sns.publish(
            PhoneNumber=number,
            Message=message
        )
        return response

    def subscribe(topic, number):
        response = sns.subscribe(
            TopicArn=topics[topic],
            Protocol="sms",
            Endpoint=number
        )
        return response

    def broadcast(topic, message):
        response = sns.publish(
            TopicArn=topics[topic],
            Message=message
        )
        return response

    def handler(message):
        sms = SMSParser(**rk.msg.unpack(message[-1]))
        try:
            if sms.action == 'send':
                response = send(sms.number, sms.message)
            elif sms.action == 'broadcast':
                response = broadcast(sms.topic, sms.message)
            elif sms.action == 'subscribe':
                response = subscribe(sms.topic, sms.number)
        except Exception as err:
            log.exception(err)
            result = 'failed...'
        else:
            metadata = response.get("ResponseMetadata")
            if metadata.get('HTTPStatusCode') == 200:
                result = 'sent...'
        finally:
            log.info(f'{sms.action} sms {result}')

    ctx = zmq.Context(1)
    sock = ctx.socket(zmq.PULL)
    sock.connect(addr)
    sock.linger = 0
    sock = ZMQStream(sock)
    sock.on_recv(handler)
    log.info('consumer started...')

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        log.info('consumer interrupted...')
    finally:
        log.info('closing consumer sockets...')
        sock.close()
        if ctx:
            ctx.term()


def producer(addr):
    ctx = zmq.Context()
    sock = ctx.socket(zmq.PUSH)
    sock.bind(addr)
    return ctx, sock


class SMSService(rk.utils.BaseService):
    _name = b'sms'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(SMSService, self).__init__(brokers, conf, verbose)
        self._setup_ipc()

        self._ctx, self._producer = producer(self._ipc)
        self._log.info('sms producer started...')

        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (
                Process(target=consumer, args=(self._ipc,)),
            )

    def __send_request(self, action, topic=None, number=None, message=None):
        data = rk.msg.pack(dict(
            action=action, number=number,
            message=message, topic=topic)
        )
        self._producer.send(data)
        return {
            'ok': True,
            'details': f'{action} request submitted for processing'
        }

    def send(self, number, message):
        return self.__send_request(
            'send', number=number, message=message
        )

    def broadcast(self, topic, message):
        return self.__send_request(
            'broadcast', topic=topic, message=message
        )

    def subscribe(self, topic, number):
        return self.__send_request(
            'subscribe', topic=topic, number=number
        )


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['sms']
    with SMSService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
