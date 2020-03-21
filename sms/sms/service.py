import zmq
import collections
from zmq.eventloop.zmqstream import ZMQStream
from tornado import ioloop
from multiprocessing import Process, Pool

import rock as rk

SMSParser = collections.namedtuple(
    'SMSParser', ('action', 'number', 'message')
)
BlastParser = collections.namedtuple(
    'SMSParser', ('action', 'topic', 'message')
)
MAX_WORKERS = 4


def consumer(addr):
    log = rk.utils.logger('sms.service')
    sns, topics = rk.aws.get_client(
        'sns', use_session=False, region='us-east-1'
    )

    def send(number, message):
        response = sns.publish(
            PhoneNumber=number,
            Message=message
        )
        metadata = response.get("ResponseMetadata")
        return metadata.get('HTTPStatusCode')

    def broadcast(topic, message):
        name = topic.replace(' ', '')
        response = sns.publish(
            TopicArn=topics[name],
            Message=message
        )
        metadata = response.get("ResponseMetadata")
        return metadata.get('HTTPStatusCode')

    def handler(message):
        data = rk.msg.unpack(message[-1])
        try:
            if data['action'] == 'send':
                sms = SMSParser(**data)
                code = send(sms.number, sms.message)
            elif data['action'] == 'broadcast':
                sms = BlastParser(**data)
                code = broadcast(sms.topic, sms.message)
        except Exception as err:
            log.exception(err)
            result = 'failed...'
        else:
            if code == 200:
                result = 'sent...'
        finally:
            log.info(f'{sms.action} sms {result}')

    ctx, sock = rk.zkit.consumer(addr, handler)
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


class SMSService(rk.utils.BaseService):
    _name = b'sms'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(SMSService, self).__init__(brokers, conf, verbose)
        self._setup_ipc()

        self._ctx, self._producer = rk.zkit.producer(self._ipc)
        self._log.info('sms producer started...')

        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (
                Process(target=consumer, args=(self._ipc,)),
            )

    def __send_request(self, data):
        self._producer.send(rk.msg.pack(data))
        action = data['action']
        res = {
            'ok': True,
            'details': f'{action} request submitted for processing'
        }
        return res

    def send(self, number, message):
        data = dict(
            action='send',
            number=number,
            message=message
        )
        return self.__send_request(data)

    def broadcast(self, topic, message):
        data = dict(
            action='broadcast',
            topic=topic,
            message=message
        )
        return self.__send_request(data)


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['sms']
    with SMSService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
