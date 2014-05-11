from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced
from urllib import quote
from bitcoinrpc import connect_to_remote

BTC_CONN = connect_to_remote('Yellowcoin', 'kyqDyBc3w2yaAgrEBTCVFAUPBYGALzLn3fZNQxwPMQWUZyhMvrgU4nT4vGmsVYTk', host='10.0.1.120')
BTC_MINCONF = 4
BTC_ACCT = 'BTC_ACCT'

balanced.Config.config(key='ak-prod-2u8Yyd0Zsg2mPbiZ7XByGixZhI6ZKCyYy')
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.postgresql_psycopg2',
		'NAME': 'yellowcoin',
		'USER': 'yellowcoin',
		'PASSWORD': 're5aTtxg3QEwsJBN9fNt9jQs',
		'HOST': 'yellowcoin.cyacjwnr6zif.us-west-2.rds.amazonaws.com',
		'PORT': '5432'
	}
}

BROKER_URL = 'sqs://AKIAIUJ4M64I3EGSNGNQ:bNPldWAN7L0e+d5hjzIZY6qOUNbm6iOAqOvJq9RT@sqs.us-west-2.amazonaws.com:80/520584774910'
BROKER_TRANSPORT_OPTIONS = { 'region' : 'us-west-2' }
