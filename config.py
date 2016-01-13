from os import environ

SECRET_KEY='secret'
REPO_DIR='/tmp/repos'
ARCHIVE_DIR='/tmp/archives'

SQLALCHEMY_DATABASE_URI = 'postgresql://bk_user:password@localhost:5432/bk_dev'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = 'development' # note this _isn't_ the salt used for bcrypt as it generates its own
SECURITY_RECOVERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_CONFIRMABLE = True
SECURITY_REGISTERABLE = True
SECURITY_EMAIL_SENDER = 'king@burgerking.cafe'
SECURITY_URL_PREFIX = '/users'
SECURITY_REGISTER_URL = '/signup'
SECURITY_POST_LOGIN_VIEW = 'users.token'
SECURITY_POST_LOGOUT_VIEW = 'main.index'
SECURITY_POST_REGISTER_VIEW = 'main.index'
SECURITY_POST_RESET_VIEW = 'main.index'
SECURITY_POST_CHANGE_VIEW = 'main.index'

MAIL_PORT = 587
MAIL_USE_TLS = True
MAIL_SERVER = environ.get('BK_EMAIL_HOST')
MAIL_USERNAME = environ.get('BK_EMAIL_USER')
MAIL_PASSWORD = environ.get('BK_EMAIL_PASS')
MAIL_DEFAULT_SENDER = 'king@burgerking.cafe'
MAIL_DEBUG = False
