from django.core.management.base import NoArgsCommand, CommandError
from time import sleep
from yellowcoin.transactions import tasks as app

minute = 60

# execute all outstanding transactions

# wrapper task to run Celery enqueuer
#	cf. http://bit.ly/1rNkWWb
class Command(NoArgsCommand):
	def handle_noargs(self, **options):
		while(True):
			app.execute_orders()
			sleep(minute)
