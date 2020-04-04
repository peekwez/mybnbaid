import functools
import rock as rk

from . import exceptions as exc

_schema = 'users'


class AuthDependency(object):
    _auth = None
    _loader = None

    def __init__(self, schema, secrets):
        self._auth = rk.utils.AuthManager(secrets)
        self._render = functools.partial(
            rk.utils.render, rk.utils.loader('users', 'emails')
        )
        self._schema = schema

    def encrypt(self, password, salt=None):
        return self._auth.encrypt_password(password, salt)

    def create_token_email(self, action, template, url, email, token):
        context = {'action_url': f'{url}/{action}?token={token}'}
        html = self._render(f'{template}.html', context)
        text = self._render(f'{template}.txt', context)
        data = {
            'token': token,
            'emails': [email],
            'subject': None,
            'html': html,
            'text': text
        }
        return data

    def login(self, user, password):
        reset_password = user.get('reset_password', None)
        if reset_password and reset_password == True:
            raise exc.ResetPassword('password reset required')

        disabled = user.get('disabled', None)
        if disabled and disabled == True:
            raise exc.UserDisabled('user account is disabled')

        _, hashed = self.encrypt(password, user['salt'])
        if hashed != user['password']:
            raise exc.BadPassword('invalid user password')

        user['token'] = self._auth.create_token('login-user', user["id"])
        return user

    def request_welcome_email(self, url, user_id, email):
        key = 'verify-email'
        token = self._auth.create_token(key, user_id)
        data = self.create_token_email(
            key, 'welcome-email', url, email, token
        )
        data['subject'] = 'Welcome to mybnbaid!'
        return data

    def request_verify_email(self, url, user_id, email):
        key = 'verify-email'
        token = self._auth.create_token(key, user_id)
        data = self.create_token_email(key, key, url, email, token)
        data['subject'] = 'Verify your email for mybnbaid'
        return data

    def verify_email(self, repo, token):
        user_id = self._auth.verify_token(
            'verify-email', token, ttl=259200
        )  # 3 days
        data = {'email_verified': True}
        _ = repo.edit(self._schema, 'users', user_id, data)
        return data

    def request_password_reset(self, url, repo, user_id):
        key = 'reset-password'
        data = {'reset_password': True}
        user = repo.edit(self._schema, 'users', user_id, data)
        token = self._auth.create_token(key, user_id)

        data = self.create_token_email(
            key, key, url, user['email'], token
        )
        data['subject'] = 'Change your password for mybnbaid'
        return data

    def reset_password(self, repo, token, password):
        user_id = self._auth.verify_token('reset-password', token, ttl=1800)
        user = repo.get(self._schema, 'users', user_id)

        # is password same as current password?
        _, hashed = self._auth.encrypt_password(password, user['salt'])
        if hashed == user['password']:
            raise exc.PasswordUsed('password has already been used')

        # is password blacklisted?
        params = (("user_id",), (user_id,))
        black = repo.filter(self._schema, 'blacklists', params)['items']
        if black:
            pk, blacklist = black[0]['id'], black[0]['passwords']
            if hashed in blacklist:
                raise exc.PasswordUsed('password has already been used')
            blacklist.append(user['password'])
            _ = repo.edit(
                self._schema, 'blacklists', pk,
                {'passwords': blacklist}
            )
        else:  # if no blacklist exist yet
            blacklist = {'user_id': user_id, 'passwords': [user['password']]}
            _ = repo.put(self._schema, 'blacklists', blacklist)

        # update user password
        data = {'password': hashed, 'reset_password': False}
        _ = repo.edit(self._schema, 'users', user_id, data)

        return True
