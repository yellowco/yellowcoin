# celery settings
#	cf. http://bit.ly/1lJvIf1

from __future__ import absolute_import
from celery import Celery
from django.conf import settings

# disallowing pickled content
#	cf. http://bit.ly/1gh3wBx
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'

app = Celery('yellowcoin')
app.config_from_object(settings)

# could import tasks (e.g. yellowcoin.transactions.tasks) manually
#	this saves us the time to find it
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)
