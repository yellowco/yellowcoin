from django.core.management.base import NoArgsCommand, CommandError
from time import sleep
from yellowcoin.transactions import tasks as app
from yellowcoin.settings.contrib.logging import log
import logging

logger = logging.getLogger('manage.daemons')

minute = 60
hour = 60 * minute

# nanny daemon to periodically add dropped actions into the queue
#	1.) each task is serialized -- only one instance will run at a time of each app
#	2.) each task calls itself via delay(task=True) at the end of execution
#	3.) if multiple instances are running, duplicate instances will halt execution

# wrapper task to run Celery enqueuer
#	cf. http://bit.ly/1rNkWWb
class Command(NoArgsCommand):
	def handle_noargs(self, **options):
		while(True):
			log(logger, 'executing ./manage.py cycle')
			app.execute_orders.delay(task=True)
			app.reset_limits.delay(task=True)
			app.clear_orders.delay(task=True)
			app.execute_recurring_orders.delay(task=True)
			sleep(hour)
