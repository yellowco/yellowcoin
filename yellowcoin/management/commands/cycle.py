from django.core.management.base import NoArgsCommand, CommandError
from time import sleep
from yellowcoin.transactions import tasks as app
from yellowcoin.settings.contrib.logging import log
import logging

logger = logging.getLogger('manage.daemons')

minute = 60

# execute all reoccuring tasks which are not executing the actual orders
#	cf. execute.py

# wrapper task to run Celery enqueuer
#	cf. http://bit.ly/1rNkWWb
class Command(NoArgsCommand):
	def handle_noargs(self, **options):
		while(True):
			log(logger, 'executing ./manage.py cycle')
			app.reset_limits()
			app.clear_orders()
			app.execute_recurring_orders()
			sleep(minute)
