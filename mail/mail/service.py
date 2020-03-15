import zmq

from tornado import ioloop

import rock as rk

from . import exceptions as exc


# logging variables
_log = rk.utils.logger('mail.service', 'INFO')

# consumer socket
_ctx = zmq.Context()
_consumer = None

# email client
_ses = None

# message protocol
_proto = rk.msg.Client(b'mpack')


def _prep_email(subject, html, text):
    return {
        "Subject": {"Data": subject, "Charset": "UTF-8"},
        "Body": {
            "Text": {"Data": text, "Charset": "UTF-8"},
            "Html": {"Data": html, "Charset": "UTF-8"}
        }
    }


def handler(message):
    _, req = rk.utils.unpack(_proto, message, 'email')
    try:
        contents = _prep_email(req.subject, req.html, req.text)
        response = _ses.send_email(
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
        _log.info(f'{req.subject} email to {req.emails} {result}')


def _setup(cfg):
    global _consumer, _ses
    _consumer = rk.zkit.consumer(_ctx, cfg['addr'], handler=handler)
    _ses = rk.aws.get_client('ses', use_session=False, region='us-east-1')
    _log.info('email consumer and aws ses client started...')


def main():
    cfg = rk.utils.parse_config('services')
    _log.info('starting email service...')
    _setup(cfg['mail'])
    try:
        ioloop.IOLoop.current().start()
    except KeyboardInterrupt:
        _log.info('email service interrupted')


if __name__ == "__main__":
    main()
