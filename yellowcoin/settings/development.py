import os
from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced

balanced.Config.config(key='ak-test-2J2vHkB6NERu57mM6vbOMylbd0X5TJSgG')

DEBUG = True

TEMPLATE_DEBUG = True

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(os.path.dirname(__file__), '..', '..', 'db.sqlite3'),
	}
}
