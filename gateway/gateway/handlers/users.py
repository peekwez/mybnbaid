from . import base


class UsersHandler(base.BaseHandler):
    _service = 'users'


handlers = [
    (r'/users.info', UsersHandler, dict(rpc='info', auth=False)),
    (r'/users.create', UsersHandler, dict(rpc='create_user', auth=False)),
    (r'/users.auth.login', UsersHandler, dict(rpc='login_user', auth=False)),
    (r'/users.auth.requestPasswordReset', UsersHandler,
     dict(rpc='request_password_reset', auth=False)),
    (r'/users.auth.setPassword', UsersHandler,
     dict(rpc='reset_password', auth=False)),
    (r'/users.auth.setEmailVerified', UsersHandler,
     dict(rpc='set_email_verified', auth=False)),
    (r'/users.auth.requestVerifyEmail',
     UsersHandler, dict(rpc='request_verify_email')),
    (r'/users.setName', UsersHandler, dict(rpc='set_name')),
    (r'/users.setPhoneNumber', UsersHandler, dict(rpc='set_phone_number')),
    (r'/users.address.create', UsersHandler, dict(rpc='create_address')),
    (r'/users.address.update', UsersHandler, dict(rpc='update_address')),
    (r'/users.address.list', UsersHandler, dict(rpc='list_address')),
    (r'/users.address.delete', UsersHandler, dict(rpc='delete_address'))
]
