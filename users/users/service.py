import rock as rk

from . import exceptions as exc
from . import authentication as _auth

_schema = 'users'
_sensitive = ('id', 'password', 'salt', 'reset_password')
_url = 'https://mybnbaid.com'


def strip_sensitive(user, fields=_sensitive):
    [user.pop(key, None) for key in fields]
    return user


class UsersService(rk.utils.BaseService):
    _name = b'users'
    _version = b'0.0.1'

    def __find_by_email(self, email):
        items = self._db.filter(
            _schema, 'users', (('email',), (email,))
        )['items']
        try:
            return items[0]
        except IndexError as err:
            return None

    def __send_mail(self, data):
        mail = rk.msg.prepare('send', data)
        res = self._clients['mail'].send(b'mail', mail)
        return res

    def __send_sms(self, action, data):
        sms = rk.msg.prepare(action, data)
        res = self._clients['sms'].send(b'sms', sms)
        return res

    def create_user(self, email, password):
        user = self.__find_by_email(email)
        if user:
            raise exc.EmailTaken('email address is taken')

        data = {"email": email}
        salt, hashed = _auth.encrypt(password)
        data.update({'salt': salt, 'password': hashed})

        user = self._db.create(_schema, 'users', data)
        user = _auth.login(user, password)

        data = _auth.request_welcome_email(
            _url, user['id'], user['email']
        )
        token = data.pop('token')
        res = self.__send_mail(data)

        user['verify_token'] = token
        return strip_sensitive(user)

    def set_name(self, user_id, first_name, last_name):
        data = {
            'first_name': first_name,
            'last_name': last_name
        }
        user = self._db.update(_schema, 'users', user_id, data)
        return strip_sensitive(user)

    def set_phone_number(self, user_id, phone_number):
        data = {'phone_number': phone_number}
        user = self._db.update(_schema, 'users', user_id, data)
        data = {
            'message': 'Welcome to mybnbaid!',
            'number': phone_number
        }
        res = self.__send_sms('send', data)
        return strip_sensitive(user)

    def create_address(self, user_id, street, city, postcode, country):
        data = {
            'user_id': user_id, 'street': street,
            'city': city, 'postcode': postcode,
            'country': country
        }
        address = self._db.create(_schema, 'addresses', data)
        return address

    def update_address(self, user_id, addr_id, street, city, postcode, country):
        data = {
            'street': street, 'city': city,
            'postcode': postcode, 'country': country
        }
        address = self._db.update(
            _schema, 'addresses', addr_id, data
        )
        return address

    def list_address(self, user_id, limit=20, offset=0):
        params = (("user_id",), (user_id,))
        kwargs = {'offset': offset, 'limit': limit}
        addresses = self._db.filter(
            _schema, 'addresses', params, **kwargs
        )
        return addresses

    def delete_address(self, user_id, addr_id):
        self._db.delete(_schema, 'addresses', addr_id)
        return {}

    def delete_user(self, user_id):
        data = {'disabled': True}
        self._db.update(_schema, 'users', user_id, data)
        return {}

    def login_user(self, email, password):
        user = self.__find_by_email(email)
        if not user:
            raise exc.UserNotFound('user does not exist')
        user = _auth.login(user, password)
        return strip_sensitive(user)

    def request_verify_email(self, user_id):
        user = self._db.get(_schema, 'users', user_id)

        data = _auth.request_verify_email(_url, user_id, user['email'])
        token = data.pop('token')
        res = self.__send_mail(data)
        return {'token': token}

    def set_email_verified(self, token):
        data = _auth.verify_email(self._db, token)
        return data

    def request_password_reset(self, email):
        user = self.__find_by_email(email)
        if not user:
            raise exc.UserNotFound('user does not exist')
        data = _auth.request_password_reset(_url, self._db, user['id'])
        token = data.pop('token')
        res = self.__send_mail(data)
        return {'token': token}

    def reset_password(self, token, password):
        passed = _auth.reset_password(self._db, token, password)
        return {'passed': True}

    def get_phone_number(self, user_id):
        user = self._db.get(_schema, 'users', user_id)
        res = {'phone_number': user.get('phone_number')}
        return res


def main():
    verbose = rk.utils.parse_config('verbose') == True
    brokers = rk.utils.parse_config('brokers')
    conf = rk.utils.parse_config('services')['users']
    _auth.init()
    with UsersService(brokers, conf, verbose) as service:
        service()


if __name__ == "__main__":
    main()
