from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from yellowcoin.currencypool.models import POOLS
from yellowcoin.transactions.tasks import get_pool
from optparse import make_option
from yellowcoin.settings.contrib.logging import log
import logging

logger = logging.getLogger('manage.deposit')

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
			help='USD:<currency> rate'),
		make_option(
			'--currency',
			action='store',
			dest='currency',
			help='virual currency (defaults to BTC)'),
	)
	def handle(self, *args, **options):
		if((not options.get('amount')) or (not options.get('exchange_rate'))):
			raise CommandError(self.help)
		if(not options.get('currency')):
			options['currency'] =  'BTC'
		try:
			pool = get_pool('USD', options.get('currency'))
			address = settings.BTC_CONN.getnewaddress(settings.BTC_ACCT)
		except Exception as e:
			print 'Exception (exiting): %s' % str(e)
			return
		pool.add(options.get('amount'), options.get('exchange_rate'))
		log(logger, '%s\t%s\t%s\t%s' % (options.get('currency'), address, options.get('amount'), options.get('exchange_rate')))
		print 'send %s %s to %s' % (options.get('amount'), options.get('currency'), address)

