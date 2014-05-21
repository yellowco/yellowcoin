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

# although ALLOWED_HOSTS = [ '.yellowco.in' ] is recommened behavior, we need to set
#	as allow_all to allow the load balancer to mask as us
# cf. http://bit.ly/1nCLPvW, http://bit.ly/RSFuBi
import requests

ALLOWED_HOSTS = [
    'yellowco.in',
]
 
EC2_PRIVATE_IP  =   None
try:
	EC2_PRIVATE_IP = requests.get('http://169.254.169.254/latest/meta-data/local-ipv4', timeout = 0.01).text
	if EC2_PRIVATE_IP:
		ALLOWED_HOSTS.append(EC2_PRIVATE_IP)
except requests.exceptions.RequestException:
	pass

# Application definition

INSTALLED_APPS = (
	'django_email_validator',
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

# cf. http://bit.ly/1sqK05z
import os.path
PROJECT_PATH = os.path.abspath(os.path.dirname(__name__))
relative = lambda path: os.path.join(PROJECT_PATH, path)

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
HOST_IP = strip(urlopen('http://icanhazip.com/s').read())

USE_X_FORWARDED_HOST = True
