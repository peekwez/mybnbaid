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


# initialize message client
_proto = rk.msg.Client(b'mpack')

# email templates
_path = os.path.dirname(os.path.abspath(__file__))
_loader = rk.utils.loader(f'{_path}/emails')


def encrypt(password, salt=None):
    return _passwd.encrypt(password, salt)


def login(user, password):
    reset_password = user.get('reset_password', None)
    if reset_password and reset_password == True:
        raise exc.ResetPassword('password reset required')

    disabled = user.get('disabled', None)
    if disabled and disabled == True:
        raise exc.UserDisabled('user account is disabled')

    _, hashed = encrypt(password, user['salt'])
    if hashed != user['password']:
        raise exc.BadPassword('invalid user password')

    user['token'] = _token.create('LOGIN', user["id"])
    return user


def request_verify_email(url, user_id, email):
    token = _token.create('VERIFY', user_id)

    action = 'verify-email'
    context = {'action_url': f'{url}/{action}?token={token}'}
    html = rk.utils.render(_loader, f'{action}.html', context)
    text = rk.utils.render(_loader, f'{action}.txt', context)
    data = {
        'token': token,
        'emails': [email],
        'subject': 'Verify email',
        'html': html,
        'text': text
    }
    return data


def verify_email(store, token):
    user_id = _token.verify('VERIFY', token, ttl=259200)  # 3 days
    data = {'email_verified': True}
    _ = store.update(_schema, 'users', user_id, data)
    return data


def request_password_reset(url, store, user_id):
    data = {'reset_password': True}
    user = store.update(_schema, 'users', user_id, data)
    token = _token.create('RESET', user_id)

    action = 'reset-password'
    context = {'action_url': f'{url}/{action}?token={token}'}
    html = rk.utils.render(_loader, f'{action}.html', context)
    text = rk.utils.render(_loader, f'{action}.txt', context)
    data = {
        'token': token,
        'emails': [user['email']],
        'subject': 'Password reset',
        'html': html,
        'text': text,
    }
    return data


def reset_password(store, token, password):
    user_id = _token.verify('RESET', token, ttl=1800)
    user = store.get(_schema, 'users', user_id)

    # is password same as current password?
    _, hashed = encrypt(password, user['salt'])
    if hashed == user['password']:
        raise exc.PasswordUsed('password has already been used')

    # is password blacklisted?
    params = (("user_id",), (user_id,))
    black = store.filter(_schema, 'blacklists', params)['items']
    if black:
        pk, blacklist = black[0]['id'], black[0]['passwords']
        if hashed in blacklist:
            raise exc.PasswordUsed('password has already been used')
        blacklist.append(user['password'])
        _ = store.update(
            _schema, 'blacklists', pk, {'passwords': blacklist}
        )
    else:  # if no blacklist exist yet
        blacklist = {'user_id': user_id, 'passwords': [user['password']]}
        _ = store.create(_schema, 'blacklists', blacklist)

    # update user password
    data = {'password': hashed, 'reset_password': False}
    _ = store.update(_schema, 'users', user_id, data)

    return True
