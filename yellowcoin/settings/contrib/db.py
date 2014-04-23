# database configurations
#	cf. http://bit.ly/1hl2DGh
import os

# postgresql
#	cf. http://bit.ly/1hpWZ13 on configuration
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

# sqlite
# DATABASES = {
#	'default': {
#		'ENGINE': 'django.db.backends.sqlite3',
#		'NAME': os.path.join(os.path.dirname(__file__), '..', '..', 'db.sqlite3'),
#	}
# }
