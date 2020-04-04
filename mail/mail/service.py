import rock as rk

MAX_WORKERS = 2


class Tasks(rk.svc.BaseTasks):
    def __init__(self, ses):
        self._ses = ses

    def send_mail(self, data):
        body = {
            'Subject': dict(Data=data['subject'], Charset='UTF-8'),
            'Body': {
                'Text': dict(Data=data['text'], Charset='UTF-8'),
                'Html': dict(Data=data['html'], Charset='UTF-8'),
            }
        }
        emails = data['emails']
        response = self._ses.send_email(
            Source='no-reply@mybnbaid.com',
            Destination={'ToAddresses': emails},
            Message=body
        )


class MailService(rk.svc.BaseService):
    _name = 'mail'
    _version = '0.0.1'

    def __init__(self, conf):
        super(MailService, self).__init__(conf)
        ses = self._sas.get_client('ses', region='us-east-1')
        self._setup_tasks(
            Tasks(ses), MAX_WORKERS
        )

    def send(self, emails, subject, html, text):
        data = dict(emails=emails, subject=subject, html=html, text=text)
        return self._emit('send:mail', data)


def main():
    conf = rk.utils.parse_config()
    with MailService(conf) as service:
        service()


if __name__ == "__main__":
    main()
