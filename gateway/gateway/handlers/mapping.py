import collections

urls = collections.OrderedDict((
    (r'/users.create', 'create_user'),
    (r'/users.auth.login', 'login_user'),
    (r'/users.auth.setEmailVerified', 'set_email_verified'),
    (r'/users.auth.requestPasswordReset', 'request_password_reset'),
    (r'/users.auth.setPassword', 'reset_password'),
    (r'/users.auth.requestVerifyEmail', 'request_verify_email'),
    (r'/users.setName', 'set_name'),
    (r'/users.setPhoneNumber', 'set_phone_number'),
    (r'/users.address.create', 'create_address'),
    (r'/users.address.update', 'update_address'),
    (r'/users.address.list', 'list_address'),
    (r'/users.address.delete', 'delete_address'),
    (r'/zones.getLocation', 'get_location'),
    (r'/zones.getCity', 'get_city'),
    (r'/zones.getRegion', 'get_region'),
    (r'/zones.locations', 'get_locations'),
    (r'/zones.cities', 'get_cities'),
    (r'/zones.regions', 'get_regions')
))
