from yellowcoin.settings.default import *
from balanced_yellowcoin import balanced

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
BROKER_URL = 'redis://localhost:6379/0'
