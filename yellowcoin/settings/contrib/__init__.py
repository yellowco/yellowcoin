"""
Django settings for yellowcoin project.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/
"""

import django.conf.global_settings as DEFAULT_SETTINGS

# logging configuration file
from yellowcoin.settings.contrib.logging import *

# blockscore API key
from yellowcoin.settings.contrib.blockscore import *

# python decimal rounding defaults to round(x <= 0.5) == 0.0
from decimal import getcontext, ROUND_HALF_UP
getcontext().rounding = ROUND_HALF_UP

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.6/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '*ygou-hx3(6=$$llo00j5i(j2^v-#61k-6$3yekjngnu_yw-kj'

# SECURITY WARNING: don't run with debug turned on in production!
# Note that turning DEBUG = False disables static file hosting
# Static files should be handled by the web server
DEBUG = False

TEMPLATE_DEBUG = False

CACHE = False

ALLOWED_HOSTS = ['*']

# Versioning system --
#	(0.0|0.1|X.0).YY.MM.DD
#	0.0 -- alpha
#	0.1 -- beta
#	X.0 -- release
VERSION_INFO = {
	'state' : 'alpha',
	'version' : 0,
	'iteration' : 0,
	'year' : 14,
	'month' : 2,
	'day' : 24,
}

# Application definition

INSTALLED_APPS = (
	'yellowcoin', # required for templatetags...?
	'grappelli', 'django.contrib.admin',
	'django.contrib.auth',
	'django.contrib.contenttypes',
	'django.contrib.sessions',
	'django.contrib.messages',
	'django.contrib.staticfiles',
	'south', 'rest_framework', 'djrill',
	'django_gravatar','template_email',
	'yellowcoin.users', 'yellowcoin.main', 'yellowcoin.transactions', 'yellowcoin.currencypool',
	'twilio',
	'django_otp',
	'django_otp_twilio_yellowcoin',
	'django_rest_framework_docs_yellowcoin',
	'django_routing_numbers',
	'xmltodict',
	'balanced_yellowcoin'
)

MIDDLEWARE_CLASSES = (
	'django.contrib.sessions.middleware.SessionMiddleware',
	'django.middleware.common.CommonMiddleware',
	'django.middleware.csrf.CsrfViewMiddleware',
	'django.contrib.auth.middleware.AuthenticationMiddleware',
	'django_otp.middleware.OTPMiddleware',
	'django.contrib.messages.middleware.MessageMiddleware',
	'django.middleware.clickjacking.XFrameOptionsMiddleware',
)

ROOT_URLCONF = 'yellowcoin.urls'

WSGI_APPLICATION = 'yellowcoin.wsgi.application'

REST_FRAMEWORK = {
	'EXCEPTION_HANDLER': 'yellowcoin.api.exceptions.yellowcoin_exception_handler',
	'DEFAULT_AUTHENTICATION_CLASSES': (
		'rest_framework.authentication.SessionAuthentication',
		'rest_framework.authentication.BasicAuthentication',
		'yellowcoin.api.authentication.YellowcoinAuthentication'
	),
	'DEFAULT_PERMISSION_CLASSES': (
		'rest_framework.permissions.IsAuthenticated'
	)
}

from yellowcoin.settings.contrib.bitcoin import *
from yellowcoin.settings.contrib.celery import *
from yellowcoin.settings.contrib.email import *
from yellowcoin.settings.contrib.geoip import *
from yellowcoin.settings.contrib.i18n import *
from yellowcoin.settings.contrib.static import *
from yellowcoin.settings.contrib.otp_twilio import *

# Grappelli configuration
GRAPPELLI_ADMIN_TITLE = 'Yellowcoin'

# Message framework settings
from django.contrib.messages import constants as message_constants
MESSAGE_TAGS = {
	message_constants.DEBUG: 'info',
	message_constants.INFO: 'info',
	message_constants.SUCCESS: 'success',
	message_constants.WARNING: 'warning',
	message_constants.ERROR: 'danger'
} # Bootstrap alert integration

# Templates
TEMPLATE_DIRS = (
	# Put strings here, like "/home/html/django_templates" or "C:/www/django/templates".
	# Always use forward slashes, even on Windows.
	# Don't forget to use absolute paths, not relative paths.
	os.path.join(os.path.dirname(__file__), '..', '..', 'templates'),
)

# Authentication
AUTH_USER_MODEL = 'users.User'

# two-factor authentication
#	cf http://bit.ly/J90jUq
LOGIN_URL = '/users/login/'
LOGIN_REDIRECT_URL = '/'

TEMPLATE_CONTEXT_PROCESSORS = DEFAULT_SETTINGS.TEMPLATE_CONTEXT_PROCESSORS + (
	'yellowcoin.main.context_processors.current_domain',
	'yellowcoin.main.context_processors.current_protocol', )

from urllib import urlopen
from string import strip

# get server IP
HOST_IP = strip(urlopen('http://wtfismyip.com/text').read())

