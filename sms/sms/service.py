import rock as rk

MAX_WORKERS = 2


class Tasks(rk.svc.BaseTasks):
    def __init__(self, sns, topics):
        self._sns = sns
        self._topics = topics

    def send_sms(self, data):
        response = self._sns.publish(
            PhoneNumber=data['number'],
            Message=data['message']
        )

    def broadcast_sms(self, data):
        name = data['topic'].replace(' ', '')
        response = self._sns.publish(
            TopicArn=self._topics[name],
            Message=data['message']
        )


class SMSService(rk.svc.BaseService):
    _name = 'sms'
    _version = '0.0.1'

    def __init__(self, conf):
        super(SMSService, self).__init__(conf)
        sns, topics = self._sas.get_client('sns', region='us-east-1')
        self._setup_tasks(Tasks(sns, topics), MAX_WORKERS)

    def send(self, number, message):
        data = dict(number=number, message=message)
        return self._emit('send:sms', data)

    def broadcast(self, topic, message):
        data = dict(topic=topic, message=message)
        return self._emit('broadcast:sms', data)


def main():
    conf = rk.utils.parse_config()
    with SMSService(conf) as service:
        service()


if __name__ == "__main__":
    main()
