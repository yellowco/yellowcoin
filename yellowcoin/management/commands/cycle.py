from django.core.management.base import NoArgsCommand, CommandError

# wrapper task to run Celery enqueuer
#	cf. http://bit.ly/1rNkWWb
class Command(NoArgsCommand):
	def handle_noargs(self, **options):
		print 'I\'m a custom command. Invoke me via ./manage.py cycle'

