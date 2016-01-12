REPO_DIR='/tmp/repos'
ARCHIVE_DIR='/tmp/archives'

SECRET_KEY='foo'
SQLALCHEMY_DATABASE_URI = 'postgresql://bk_user:password@localhost:5432/bk_dev'
SQLALCHEMY_TRACK_MODIFICATIONS = False

SECURITY_PASSWORD_HASH = 'bcrypt'
SECURITY_PASSWORD_SALT = 'development' # note this _isn't_ the salt used for bcrypt as it generates its own
SECURITY_RECOVERABLE = True
SECURITY_CHANGEABLE = True
SECURITY_CONFIRMABLE = True
SECURITY_REGISTERABLE = True
SECURITY_EMAIL_SENDER = 'bk@burgerking.cafe'
SECURITY_URL_PREFIX = '/users'
SECURITY_REGISTER_URL = '/signup'
