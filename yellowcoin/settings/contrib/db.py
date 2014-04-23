# Database
# https://docs.djangoproject.com/en/1.6/ref/settings/#databases
import os
DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(os.path.dirname(__file__), '..', '..', 'db.sqlite3'),
	}
}
