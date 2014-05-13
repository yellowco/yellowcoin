from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced
from urllib import quote
from bitcoinrpc import connect_to_remote

BTC_CONN = connect_to_remote('Yellowcoin', 'kyqDyBc3w2yaAgrEBTCVFAUPBYGALzLn3fZNQxwPMQWUZyhMvrgU4nT4vGmsVYTk', host='10.0.1.92')
BTC_MINCONF = 4
BTC_ACCT = 'BTC_ACCT'

balanced.Config.config(key='ak-test-1GGZIycz4QreXAVxxwJWl2xotuvlZsqmW')
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql_psycopg2',
		'NAME': 'development',
		'USER': 'root',
		'PASSWORD': 'monkeys123',
		'HOST': 'development.cyacjwnr6zif.us-west-2.rds.amazonaws.com',
		'PORT': '5432'
	}
}

# celery connection information

BROKER_USER = 'AKIAJOHT4G2TVXQ3HVEA'
BROKER_PASSWORD = 'K2e74QhKftjtoMAXCRPZUbQeTJygismKH2OQrNXy'
BROKER_TRANSPORT = 'sqs'
BROKER_URL = 'sqs://%s:%s@' % (BROKER_USER, BROKER_PASSWORD)
BROKER_TRANSPORT_OPTIONS = { 'region' : 'us-west-2' }

CELERY_DEFAULT_QUEUE = 'production'
CELERY_QUEUES = {
	CELERY_DEFAULT_QUEUE: {
		'exchange': CELERY_DEFAULT_QUEUE,
		'binding_key': CELERY_DEFAULT_QUEUE
	}
}

# Django caching framework -- for now, we shall use the filesystem to store the cache
CACHES = {
	'default': {
		'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
		'LOCATION': './cache/staging/',
	}
}

