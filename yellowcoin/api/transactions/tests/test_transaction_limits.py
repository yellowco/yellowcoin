from yellowcoin.currencypool.models import POOLS
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from yellowcoin.transactions.models import TransactionLimit
from yellowcoin.users.models import User
from yellowcoin.api.tests import YellowcoinAPITestCase
from decimal import Decimal

class TestTransactionLimits(YellowcoinAPITestCase):
	def test_transaction_limits(self):
		response = self.client.get('/api/limits/')
		self.assertEqual(response.status_code, 200)
		self.assertTrue('USD' in response.data)
		self.assertTrue('BTC' in response.data)
		self.assertEqual(response.data['USD']['cur_amount'], '0')
		limit = TransactionLimit.objects.create(user=self.base_user, currency='USD', cur_amount=0, override=True)
		limit.max_amount = 100
		limit.save()
		response = self.client.get('/api/limits/')
		self.assertEqual(response.status_code, 200)
		self.assertTrue('USD' in response.data)
		self.assertTrue('BTC' in response.data)
		self.assertEqual(response.data['USD']['max_amount'], Decimal('100')) # ? not sure why this happens...?
