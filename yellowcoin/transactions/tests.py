from yellowcoin.api.tests import YellowcoinAPITestCase
from yellowcoin.api.exceptions import InsufficientFundsException
from yellowcoin.transactions.tasks import execute_orders, execute_recurring_orders
from yellowcoin.transactions.models import Transaction, RecurringOrder
from yellowcoin.currencypool.models import POOLS
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from bitcoind_emulator import EmulatedBitcoinConnection
from django.conf import settings
from django.core.management import reset_limits
from django.test.utils import override_settings
from decimal import Decimal

def CALCULATE_TEST_FEE(val, currency):
	return val * Decimal('0.01')
@override_settings(BTC_CONN=EmulatedBitcoinConnection(),
	CALCULATE_FEE=CALCULATE_TEST_FEE
)
class TestTransactions(YellowcoinAPITestCase):
	def setUp(self):
		super(TestTransactions, self).setUp()
		self.bank = self.create_bank_account()
		self.btc = self.create_btc_account()
		self.verify_bank_account(self.bank.data['id'])

	def test_btc_order(self):
		order = self.create_order(self.bank.data['id'], self.btc.data['id'])
		self.assertEqual(order.status_code, 201, order.data)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized')
		self.assertEqual(self.client.get('/api/limits/').data['BTC']['max_amount'], Decimal('0.1'))
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 3) # higher than the bid 0.02 for ask 0.01 created
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized', response.data)
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 1) # lower than the bid 0.02 for ask 0.01 created
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Initialized', response.data)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Queried') # check that pending is skipped
		execute_orders() # if payment network is in test mode, this should auto complete
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Received') # check that the tx is received
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 1)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Completed')
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 1)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Completed')

		self.assertEqual(settings.BTC_CONN.getreceivedbyaddress(address='15AeuxTuPQpntVvq4KVGqSxZM3ry39PV6Q', minconf=0), 0.0495)
		self.assertEqual(len(settings.BTC_CONN.listtransactions(address='15AeuxTuPQpntVvq4KVGqSxZM3ry39PV6Q')), 1)

	def test_usd_order(self):
		order = self.client.post('/api/orders/usd/btc/', {
			'bid_subtotal':0.1,
			'ask_subtotal':0.05,
			'withdrawal_account':self.btc.data['id'],
			'deposit_account':self.bank.data['id']
		})
		self.assertEqual(order.status_code, 201)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized')
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(100, 1) # exchange rate condition not met
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(100, 0.05) # exchange rate condition not met
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized', response.data)
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].remove(100) # raise the relative price
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Initialized', response.data)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Pending', response.data)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Pending', response.data)
		self.assertIsNotNone(response.data['deposit_address'])
		settings.BTC_CONN.sendtoaddress(response.data['deposit_address'], 0.05)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Pending', response.data)
		settings.BTC_CONN.sendtoaddress(response.data['deposit_address'], 0.1)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Pending', response.data) # transactions not confirmed
		tx = settings.BTC_CONN.listtransactions(address=response.data['deposit_address'])
		settings.BTC_CONN.gettransaction(tx[0].txid).confirmations = 10 # lol
		self.assertAlmostEqual(settings.BTC_CONN.getreceivedbyaddress(response.data['deposit_address'], minconf=4), 0.05)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Pending', response.data) # transactions not confirmed
		tx[1].confirmations = 10
		self.assertAlmostEqual(settings.BTC_CONN.getreceivedbyaddress(response.data['deposit_address'], minconf=4), 0.15)
		# Minke to Kevin -- P -> R directly for bitcoins, no Q stage
		# execute_orders()
		# self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		# self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		# response = self.client.get('/api/transactions/%s/' % order.data['id'])
		# self.assertEqual(response.status_code, 200)
		# self.assertEqual(response.data['status'], 'Queried', response.data)
		# self.assertAlmostEqual(settings.BTC_CONN.getreceivedbyaddress('15AeuxTuPQpntVvq4KVGqSxZM3ry39PV6Q', minconf=0), 0.05)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Received', response.data)
		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 1)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Completed', response.data)
	
	def test_limits(self):
		order1 = self.create_order(self.bank.data['id'], self.btc.data['id'])
		order2 = self.client.post('/api/orders/btc/usd/', {
			'bid_subtotal':0.01,
			'ask_subtotal':self.client.get('/api/limits/').data['BTC'],
			'withdrawal_account':self.bank.data['id'],
			'deposit_account':self.btc.data['id']
		})
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 1) # lower than the bid 0.02 for ask 0.01 created
		response = self.client.get('/api/transactions/%s/' % order1.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized', response.data)
		response = self.client.get('/api/transactions/%s/' % order2.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized', response.data)
		execute_orders()
		response = self.client.get('/api/transactions/%s/' % order1.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Initialized', response.data)
		response = self.client.get('/api/transactions/%s/' % order2.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Uninitialized', response.data)
		reset_limits()
		execute_orders()
		response = self.client.get('/api/transactions/%s/' % order1.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Queried', response.data)
		response = self.client.get('/api/transactions/%s/' % order2.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Initialized', response.data)
	
	def test_fail_return_to_pool(self):
		order = self.create_order(self.bank.data['id'], self.btc.data['id'])
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 3)
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(0.04, 1)
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(0.01, 0.5)
		self.assertEqual(POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].exchange_rate, 0.5)
		execute_orders() # init
		execute_orders()
		self.assertEqual(POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].exchange_rate, 1)

	def test_fail_queried(self):
		order = self.create_order(self.bank.data['id'], self.btc.data['id'])
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 1)
		execute_orders() # init
		execute_orders() # queried
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 405)
		response = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['status'], 'Queried', response)
		execute_orders()
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 405)
		self.assertEqual(self.client.get('/api/transactions/%s/' % order.data['id']).data['status'], 'Received')
		execute_orders()
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 405)
		self.assertEqual(self.client.get('/api/transactions/%s/' % order.data['id']).data['status'], 'Completed')
		execute_orders()
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 405)
		self.assertEqual(self.client.get('/api/transactions/%s/' % order.data['id']).data['status'], 'Completed')

	def test_delete_order(self):
		order = self.create_order(self.bank.data['id'], self.btc.data['id'])

		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 1)

		execute_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 1)
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 204)
		self.assertEqual(self.client.delete('/api/orders/%s/' % order.data['id']).status_code, 404)
		self.assertEqual(self.client.get('/api/orders/%s/' % order.data['id']).status_code, 404)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 0)
		tx = Transaction.objects.get(order__id=order.data['id'])
		self.assertEqual(tx.status, 'D')
		execute_orders()
		tx = Transaction.objects.get(order__id=order.data['id'])
		self.assertEqual(tx.status, 'A')
		self.assertEqual(self.client.get('/api/orders/%s/' % order.data['id']).status_code, 404)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 0)
		
	def test_recurring_order(self):
		template = self.create_order_template(self.bank.data['id'], self.btc.data['id'])
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		response = self.client.post('/api/orders/recurring/', {
			'template':template.data['id'],
			'interval':5,
			'first_run':'2014-01-25T10:32:02Z'
		})
		self.assertEqual(response.status_code, 201, response)
		execute_recurring_orders()
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		order = RecurringOrder.objects.get(id=response.data['id'])
		order.last_run = '2014-01-25T10:32:02Z'
		order.save()
		self.assertRaises(InsufficientFundsException, execute_recurring_orders)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC].add(10, 1) # lower than the bid 0.02 for ask 0.01 created
		for i in range(2): # execute twice, check the second skips
			execute_recurring_orders()
			self.assertEqual(len(self.client.get('/api/orders/').data), 0) #make sure they do not appear
			self.assertEqual(len(self.client.get('/api/transactions/').data), 1) #make sure they do appear
		self.assertIsNotNone(self.client.get('/api/orders/recurring/%s/' % response.data['id']).data['last_run'])
