import zmq

from tornado import ioloop

import rock as rk


# logging variables
_log = rk.utils.logger('sms.service', 'INFO')

# consumer socket
_ctx = zmq.Context()
_consumer = None

# sms client
_sns = None
_topics = {}

# message protocol
_proto = rk.msg.Client(b'mpack')


def send(number, message):
    response = _sns.publish(
        PhoneNumber=number,
        Message=message
    )
    return response.get('ResponseMetadata')


def subscribe(topic, number):
    response = _sns.subscribe(
        TopicArn=_topics[topic],
        Protocol="sms",
        Endpoint=number
    )
    return response.get('ResponseMetadata')


def publish(topic, message):
    response = _sns.publish(
        TopicArn=_topics[topic],
        Message=message
    )
    return response.get('ResponseMetadata')


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


def main():
    cfg = rk.utils.parse_config('services')
    _log.info('starting sms service...')
    _setup(cfg['sms'])
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('sms service interrupted')


if __name__ == "__main__":
    main()
