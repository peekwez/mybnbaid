import os

import rock as rk

from . import exceptions as exc

_schema = 'users'

# get api secrets/keys
_prod = os.environ.get('MYBNBAID-PROD', False)
_name = 'DEV_TOKEN_SECRETS'
if _prod:
    _name = 'PROD_TOKEN_SECRETES'
_secrets = rk.aws.get_secret(_name)

# initiate authentication clients
_token = rk.auth.TokenManager(_secrets)
_passwd = rk.auth.PasswordManager()

# initialize email producer
_push_email = None

# initialize message client
_msg = rk.msg.Client(b'mpack')


def encrypt(password, salt=None):
    return _passwd.encrypt(password, salt)


def login(user, password):
    reset_password = user.get('reset_password', None)
    if reset_password and reset_password == True:
        raise exc.ResetPassword('password reset required')

    disabled = user.get('disabled', None)
    if disabled and disabled == True:
        raise exc.UserDisabled('user account is disabled')

    passed = _passwd.check(user, password)
    if passed == False:
        raise exc.BadPassword('invalid user password')

    user['token'] = _token.create('LOGIN', user["id"])
    return user


def request_verify_email(user_id, email):
    token = _token.create('VERIFY', user_id)
    url = 'https://mybnbaid.com'
    link = f'{url}/verify-email?token={token}'
    # html = getfrom jinja2(token)
    html = None
    data = {
        'email': email,
        'subject': 'Verify email',
        'html': html
    }
    #_msg.send(_push_email, data)
    return True


def verify_email(store, token):
    user_id = _token.verify('VERIFY', token, ttl=259200)  # 3 days
    data = {'email_verified': True}
    _ = store.update(_schema, 'users', user_id, data)
    return data


def request_password_reset(store, user_id):
    data = {'reset_password': True}
    user = store.update(_schema, 'users', user_id, data)
    token = _token.create('RESET', user_id)
    url = 'https://mybnbaid.com'
    link = f'{url}/reset-password?token={token}'
    # html = getfrom jinja2(token)
    html = None
    data = {
        'email': user['email'],
        'subject': 'Password reset',
        'html': html
    }
    #_msg.send(_push_email, data)
    return True


def reset_password(store, token, password):
    user_id = _token.verify('RESET', token, ttl=1800)
    user = store.get(_schema, 'users', user_id)

    # is password same as current password?
    passed = _passwd.check(user, password)
    if passed == True:
        raise exc.PasswordUsed('password has already been used')

    # encrypt password
    data = _passwd.encrypt(user['salt'], password)

    # is password blacklisted?
    params = (("user_id",), (user_id,))
    black = store.filter(_schema, 'blacklists', params)
    if black:
        passwords = black[0]['passwords']
        if data['password'] & passwords:
            raise exc.PasswordUsed('password has already been used')
        pk = black[0]['id']
        passwords.add(user['password'])
        _ = store.update(_schema, 'blacklists', pk, {'password': passwords})
    else:
        black = {'passwords': {user['password']}}
        _ = store.create(_schema, 'blacklists', black)

    # update user password
    data.update({'reset_password': False})
    _ = store.update(_schema, 'users', user_id, data)

    return True
