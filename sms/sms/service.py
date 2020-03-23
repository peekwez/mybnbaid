import collections

import rock as rk

SMSParser = collections.namedtuple(
    'SMSParser', ('number', 'message')
)
BroadcastParser = collections.namedtuple(
    'SMSParser', ('topic', 'message')
)
MAX_WORKERS = 4


class SMSConsumer(rk.utils.BaseConsumer):
    def __init__(self, addr, name):
        super(SMSConsumer, self).__init__(addr, name)
        self._sns, self._topics = rk.aws.get_client(
            'sns', use_session=False, region='us-east-1'
        )

    def send(self, data):
        opts = SMSParser(**data)
        response = self._sns.publish(
            PhoneNumber=opts.number,
            Message=opts.message
        )
        return rk.aws.parse_response(response)

    def broadcast(self, data):
        opts = BroadcastParser(**data)
        name = opts.topic.replace(' ', '')
        response = self._sns.publish(
            TopicArn=self._topics[name],
            Message=opts.message
        )
        return rk.aws.parse_response(response)


class SMSService(rk.utils.BaseService):
    _name = b'sms'
    _version = b'0.0.1'

    def __init__(self, brokers, conf, verbose):
        super(SMSService, self).__init__(brokers, conf, verbose)
        self._setup_events(SMSConsumer, MAX_WORKERS)

    def send(self, number, message):
        data = dict(number=number, message=message)
        return self._emit('send', data)

    def broadcast(self, topic, message):
        data = dict(topic=topic, message=message)
        return self._emit('broadcast', data)


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['sms']
    with SMSService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
