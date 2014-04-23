from __future__ import absolute_import
import os
from celery import Celery
from django.conf import settings
from celery.utils.log import get_task_logger

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'yellowcoin.settings.production')

app = Celery('yellowcoin')

app.config_from_object('django.conf:settings')
app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

logger = get_task_logger(__name__)

@app.task(bind=True)
def debug_task(self):
	print('Request: {0!r}'.format(self.request))
