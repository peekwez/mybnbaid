import rock as rk

from . import exceptions as exc
from . import authentication as auth

_schema = 'users'
_sensitive = ('id', 'password', 'salt', 'reset_password')
_url = 'https://mybnbaid.com'


def strip_sensitive(user, fields=_sensitive):
    [user.pop(key, None) for key in fields]
    return user


class UsersService(rk.svc.BaseService):
    _name = 'users'
    _version = '0.0.1'
    _auth = None
    _mail_rpc = None
    _sms_prc = None

    def _setup_clients(self, broker, verbose):
        self._mail_rpc = rk.rpc.RpcProxy(broker, 'mail', verbose)
        self._sms_rpc = rk.rpc.RpcProxy(broker, 'sms', verbose)

    def _setup_auth(self, secrets):
        self._auth = auth.AuthDependency(_schema, secrets)

    def _find_by_email(self, email):
        items = self._repo.filter(
            _schema, 'users', (('email',), (email,))
        )['items']
        try:
            return items[0]
        except IndexError as err:
            return None

    def create_user(self, email, password):
        user = self._find_by_email(email)
        if user:
            raise exc.EmailTaken('email address is taken')

        data = dict(email=email)
        salt, hashed = self._auth.encrypt(password)
        data.update(dict(salt=salt, password=hashed))

        user = self._repo.put(_schema, 'users', data)
        user = self._auth.login(user, password)
        data = self._auth.request_welcome_email(
            _url, user['id'], user['email']
        )
        token = data.pop('token')
        res = self._mail_rpc.send(**data)
        user['verify_token'] = token
        return strip_sensitive(user)

    def set_name(self, user_id, first_name, last_name):
        data = dict(first_name=first_name, last_name=last_name)
        user = self._repo.edit(_schema, 'users', user_id, data)
        return strip_sensitive(user)

    def set_phone_number(self, user_id, phone_number):
        data = dict(phone_number=phone_number)
        user = self._repo.edit(_schema, 'users', user_id, data)
        res = self._sms_rpc.send(
            number=phone_number,
            message='Welcome to mybnbaid!'
        )
        return strip_sensitive(user)

    def create_address(self, user_id, street, city, postcode, country):
        data = dict(
            user_id=user_id, street=street, city=city,
            postcode=postcode, country=country
        )
        address = self._repo.put(_schema, 'addresses', data)
        return address

    def update_address(self, user_id, addr_id, street, city, postcode, country):
        data = dict(
            street=street, city=city,
            postcode=postcode, country=country
        )
        address = self._repo.edit(
            _schema, 'addresses', addr_id, data
        )
        return address

    def list_address(self, user_id, limit=20, offset=0):
        params = (("user_id",), (user_id,))
        kwargs = dict(offset=offset, limit=limit)
        addresses = self._repo.filter(
            _schema, 'addresses', params, **kwargs
        )
        return addresses

    def delete_address(self, user_id, addr_id):
        self._repo.drop(_schema, 'addresses', addr_id)
        return {}

    def delete_user(self, user_id):
        data = dict(disabled=True)
        self._repo.edit(_schema, 'users', user_id, data)
        return {}

    def login_user(self, email, password):
        user = self._find_by_email(email)
        if not user:
            raise exc.UserNotFound('user does not exist')
        user = self._auth.login(user, password)
        return strip_sensitive(user)

    def request_verify_email(self, user_id):
        user = self._repo.get(_schema, 'users', user_id)

        data = self._auth.request_verify_email(_url, user_id, user['email'])
        token = data.pop('token')
        res = self._mail_rpc.send(**data)
        return dict(token=token)

    def set_email_verified(self, token):
        data = self._auth.verify_email(self._repo, token)
        return data

    def request_password_reset(self, email):
        user = self._find_by_email(email)
        if not user:
            raise exc.UserNotFound('user does not exist')
        data = self._auth.request_password_reset(_url, self._repo, user['id'])
        token = data.pop('token')
        res = self._mail_rpc.send(**data)
        return dict(token=token)

    def reset_password(self, token, password):
        passed = self._auth.reset_password(self._repo, token, password)
        return dict(passed=True)

    def get_phone_number(self, user_id):
        user = self._repo.get(_schema, 'users', user_id)
        return dict(phone_number=user.get('phone_number'))


def main():
    conf = rk.utils.parse_config()
    with UsersService(conf) as service:
        service()


if __name__ == "__main__":
    main()
