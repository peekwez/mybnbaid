import zmq

from tornado import ioloop

import rock as rk


SMSParser = collections.namedtuple(
    'SMSParser', ('action', 'topic', 'number', 'message')
)


def consumer(addr):
    log = rk.utils.logger('sms.service')
    sns = rk.aws.get_client(
        'sns', use_session=False, region='us-east-1'
    )
    topics = sns.list_topics()['Topics']
    if topics:
        for topic in topics:
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
    log.info('sms consumer started...')

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


def handler(message):
    _, req = rk.utils.unpack(_proto, message, 'sms')
    try:
        if req.action == 'send':
            res = send(req.number, req.message)
        elif req.action == 'publish':
            res = publish(req.topic, req.message)
        elif req.action == 'subscribe':
            res = subscribe(req.topic, req.number)
    except Exception as err:
        _log.exception(err)
        result = 'failed...'
    else:
        _log.info(f'{req.action} sms request processed...')
    finally:
        pass


def _setup(cfg):
    global _consumer, _sns, _topics
    _consumer = rk.zkit.consumer(_ctx, cfg['addr'], handler=handler)
    _sns = rk.aws.get_client('sns', use_session=False, region='us-east-1')
    topics = _sns.list_topics()['Topics']
    if topics:
        for topic in topics:
            arn = topic['TopicArn']
            name = arn.split(':')[-1]
            _topics[name] = arn
    _log.info('consumer and aws sns client started...')


class SMSService(rk.utils.BaseService):
    __slots__ = ('_ctx', '_unix', '_addr', '_producer', '_consumers')
    _name = b'sms'
    _version = b'0.0.1'
    _log = rk.utils.logger('sms.service')

    def __init__(self, brokers, conf, verbose):
        super(SMSService, self).__init__(brokers, conf, verbose)
        self._unix = f'/tmp/sms.{os.getpid()}.sock'
        self._addr = f'ipc://{self._unix}'
        self._ctx, self._producer = producer(self._addr)
        self._log.info('sms producer started...')
        self._consumers = ()
        for num in range(MAX_WORKERS):
            self._consumers += (Process(target=consumer, args=(self._addr,)),)

    def __exit__(self, type, value, traceback):
        super(SMSService, self).__exit__(type, value, traceback)
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
        super(SMSService, self).__call__()

    def __send_request(self, action, topic=None, number=None, message=None):
        data = rk.msg.pack(dict(
            action='send', number=number,
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
