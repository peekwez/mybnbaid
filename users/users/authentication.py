import rock as rk

from . import exceptions as exc

_schema = 'users'

# initialize token clients
_token = None
_passwd = None

# email templates
_loader = None


def init():
    global _token, _passwd, _loader
    _token = rk.auth.TokenManager(rk.aws.get_token_secrets())
    _passwd = rk.auth.PasswordManager()
    _loader = rk.utils.loader('users', 'emails')


def encrypt(password, salt=None):
    return _passwd.encrypt(password, salt)


def create_token_email(action, template, url, email, token):
    context = {'action_url': f'{url}/{action}?token={token}'}
    html = rk.utils.render(_loader, f'{template}.html', context)
    text = rk.utils.render(_loader, f'{template}.txt', context)
    data = {
        'token': token,
        'emails': [email],
        'subject': None,
        'html': html,
        'text': text
    }
    return data


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


def request_welcome_email(url, user_id, email):
    token = _token.create('VERIFY', user_id)
    data = create_token_email(
        'verify-email', 'welcome-email', url, email, token
    )
    data['subject'] = 'Welcome to mybnbaid!'
    return data


def request_verify_email(url, user_id, email):
    token = _token.create('VERIFY', user_id)
    data = create_token_email(
        'verify-email', 'verify-email', url, email, token)
    data['subject'] = 'Verify your email for mybnbaid'
    return data


def verify_email(db, token):
    user_id = _token.verify('VERIFY', token, ttl=259200)  # 3 days
    data = {'email_verified': True}
    _ = db.update(_schema, 'users', user_id, data)
    return data


def request_password_reset(url, db, user_id):
    data = {'reset_password': True}
    user = db.update(_schema, 'users', user_id, data)
    token = _token.create('RESET', user_id)

    data = create_token_email(
        'reset-password', 'reset-password', url, user['email'], token
    )
    data['subject'] = 'Change your password for mybnbaid'
    return data


def reset_password(db, token, password):
    user_id = _token.verify('RESET', token, ttl=1800)
    user = db.get(_schema, 'users', user_id)

    # is password same as current password?
    _, hashed = encrypt(password, user['salt'])
    if hashed == user['password']:
        raise exc.PasswordUsed('password has already been used')

    # is password blacklisted?
    params = (("user_id",), (user_id,))
    black = db.filter(_schema, 'blacklists', params)['items']
    if black:
        pk, blacklist = black[0]['id'], black[0]['passwords']
        if hashed in blacklist:
            raise exc.PasswordUsed('password has already been used')
        blacklist.append(user['password'])
        _ = db.update(
            _schema, 'blacklists', pk, {'passwords': blacklist}
        )
    else:  # if no blacklist exist yet
        blacklist = {'user_id': user_id, 'passwords': [user['password']]}
        _ = db.create(_schema, 'blacklists', blacklist)

    # update user password
    data = {'password': hashed, 'reset_password': False}
    _ = db.update(_schema, 'users', user_id, data)

    return True
