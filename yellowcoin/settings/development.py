import os
from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced
from bitcoinrpc import connect_to_remote
from bitcoind_emulator import EmulatedBitcoinConnection

BTC_CONN = EmulatedBitcoinConnection()
MIN_CONF = 4
BTC_ACCT = 'BTC_ACCT'

balanced.Config.config(key='ak-test-2J2vHkB6NERu57mM6vbOMylbd0X5TJSgG')

MAX_USERS = 10

DEBUG = True

TEMPLATE_DEBUG = True

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(os.path.dirname(__file__), '..', '..', 'db.sqlite3'),
	}
}

AWS_ACCESS_KEY_ID = 'AKIAJOHT4G2TVXQ3HVEA'
AWS_SECRET_ACCESS_KEY = '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'
BROKER_TRANSPORT = 'sqs'
BROKER_URL = 'sqs://%s:%s@' % (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY)
BROKER_TRANSPORT_OPTIONS = { 'region' : 'us-west-2' }

CELERY_DEFAULT_QUEUE = 'development'
CELERY_QUEUES = {
	CELERY_DEFAULT_QUEUE: {
		'exchange': CELERY_DEFAULT_QUEUE,
		'binding_key': CELERY_DEFAULT_QUEUE
	}
}

# Django caching framework -- for now, we shall use the filesystem to store the cache
#	cf. http://bit.ly/1lpF93B
CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
		'LOCATION': './cache/development/',
	}
}

