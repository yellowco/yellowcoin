# database configurations
#	cf. http://bit.ly/1hl2DGh
import os

DATABASES = {
	'default': {
		'ENGINE': 'django.db.backends.sqlite3',
		'NAME': os.path.join(os.path.dirname(__file__), '..', '..', 'db.sqlite3'),
	}
}
