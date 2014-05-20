from django.core.management.base import BaseCommand, CommandError
from yellowcoin.currencypool.models import POOLS
from yellowcoin.transactions.tasks import get_pool
from optparse import make_option

class Command(BaseCommand):
	args = 'amount rate'
	help = 'invalid or incomplete arguments -- try running with -h for list of available options'
	# list of input options for this command
	#	cf. http://bit.ly/1h1IVMp, http://bit.ly/1jx8VFa
	option_list = BaseCommand.option_list + (
		make_option(
			'--amount',
			action='store',
			dest='amount',
			help='amount of BTC to deposit'),
		make_option(
			'--exchange_rate',
			action='store',
			dest='exchange_rate',
			help='USD:BTC rate')
	)
	def handle(self, *args, **options):
		if((not options.get('amount')) or (not options.get('exchange_rate'))):
			raise CommandError(self.help)
		pool = get_pool('USD', 'BTC')
		pool.add(options.get('amount'), options.get('exchange_rate'))

