from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced
from urllib import quote
from bitcoinrpc import connect_to_remote

BTC_CONN = connect_to_remote('Yellowcoin', 'kyqDyBc3w2yaAgrEBTCVFAUPBYGALzLn3fZNQxwPMQWUZyhMvrgU4nT4vGmsVYTk', host='10.0.1.92')
MIN_CONF = 4
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

# celery broker -- where the active task queue resides
BROKER_URL = 'sqs://AKIAJOHT4G2TVXQ3HVEA:K2e74QhKftjtoMAXCRPZUbQeTJygismKH2OQrNXy@sqs.us-west-2.amazonaws.com:80/520584774910'
BROKER_TRANSPORT_OPTIONS = { 'region' : 'us-west-2' }
