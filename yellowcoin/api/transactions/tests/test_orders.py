from django.test.utils import override_settings
from django.conf import settings
from yellowcoin.currencypool.models import POOLS
from yellowcoin.transactions.models import Transaction
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from yellowcoin.api.tests import YellowcoinAPITestCase

class TestOrders(YellowcoinAPITestCase):
	def test_orders(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()

		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		self.assertEqual(self.client.post('/api/orders/').status_code, 400)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 0)
		self.assertEqual(self.create_order(bank.data['id'], btc.data['id']).status_code, 400)
		self.verify_bank_account(bank.data['id'])
		self.assertEqual(self.create_order(bank.data['id'], bank.data['id']).status_code, 400)
		self.assertEqual(self.create_order(btc.data['id'], btc.data['id']).status_code, 400)
		response = self.create_order(bank.data['id'], btc.data['id'])
		self.assertEqual(response.status_code, 201)
		self.assertIsNotNone(response.data['id'])
		self.assertEqual(self.client.get('/api/orders/%s/' % response.data['id']).status_code, 200)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		transaction = self.client.get('/api/transactions/')
		self.assertEqual(transaction.status_code, 200)
		self.assertEqual(transaction.data[0]['status'], 'Uninitialized')
		self.assertEqual(transaction.data[0]['order']['id'], response.data['id'])
		self.assertEqual(transaction.data[0]['withdrawal_account']['id'], bank.data['id'])
		self.assertEqual(transaction.data[0]['deposit_account']['id'], btc.data['id'])
		Transaction.objects.all().update(status='C') # set all to complete
		self.assertEqual(len(self.client.get('/api/orders/').data), 1)
	def test_order_crossover(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		order = self.create_order(bank.data['id'], btc.data['id'])
		self.client.logout()
		secondary = self.create_user('test2@test.com')
		self.client.login(username='test2@test.com', password='test')
		self.assertEqual(len(self.client.get('/api/transactions/').data), 0)
		self.assertEqual(self.client.get('/api/transactions/%s/' % order.data['id']).status_code, 404, order.data)
		secondary.profile.payment_network.delete()

	def test_exceeds_limits(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		response = self.client.post('/api/orders/btc/usd/', {
			'bid_subtotal':1000000000000,
			'ask_subtotal':1000000000000,
			'withdrawal_account':bank.data['id'],
			'deposit_account':btc.data['id']
		})
		self.assertEqual(response.status_code, 400)
		self.assertTrue('bid_subtotal' in response.data['detail'])
		self.assertTrue('ask_subtotal' in response.data['detail'])
		response = self.client.post('/api/orders/btc/usd/', {
			'bid_subtotal':0,
			'ask_subtotal':0
		})
		self.assertEqual(response.status_code, 400)
		self.assertTrue('bid_subtotal' in response.data['detail'])
		self.assertTrue('ask_subtotal' in response.data['detail'])

		with self.settings(MIN_USD_TX=50.00):
			response = self.client.post('/api/orders/btc/usd/', {
				'bid_subtotal' : 1,
				'ask_subtotal' : 0.01,
				'withdrawal_account' : bank.data['id'],
				'deposit_account' : btc.data['id']
			})
		self.assertEqual(response.status_code, 400, "Small orders were permitted!")

		self.assertTrue('bid_subtotal' in response.data['detail'], response)
		self.assertTrue('ask_subtotal' not in response.data['detail'])
	def test_delete_order(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		response = self.client.post('/api/orders/usd/btc/', {
			'bid_subtotal':0.05,
			'ask_subtotal':0.1,
			'withdrawal_account':btc.data['id'],
			'deposit_account':bank.data['id']
		})
		self.assertEqual(response.status_code, 201, response.content)
		self.assertEqual(self.client.delete('/api/orders/%s/' % response.data['id']).status_code, 204)
	def test_order_from_template(self):
		POOLS['USD']['BTC'].add(10, 2)
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		template = self.create_order_template(bank.data['id'], btc.data['id'])
		order = self.client.post('/api/orders/btc/usd/', {'order_template':template.data['id']})
		self.assertEqual(order.status_code, 201)
		self.assertEqual(self.client.post('/api/orders/', {'order_template':template.data['id']}).status_code, 201)
		self.assertEqual(self.client.post('/api/orders/usd/btc/', {'order_template':template.data['id']}).status_code, 400)
		self.assertIsNotNone(order.data['id'])
		tx = self.client.get('/api/transactions/%s/' % order.data['id'])
		self.assertEqual(tx.data['withdrawal_account']['id'], template.data['withdrawal_account'])
		self.assertEqual(tx.data['deposit_account']['id'], template.data['deposit_account'])
	def test_one_click_order(self):
		POOLS['USD']['BTC'].add(10, 2)
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		one_click = self.client.get('/api/settings/').data['one_click_order_template']['id']
		self.assertIsNotNone(one_click)
		self.assertEqual(self.client.put('/api/orders/templates/%s/' % one_click, {
			'bid_currency':'USD',
			'ask_currency':'BTC',
			'withdrawal_account':bank.data['id'],
			'deposit_account':btc.data['id'],
			'type':'A',
			'subtotal':0.05
		}).status_code, 200)
		self.assertEqual(self.client.post('/api/orders/', {
			'one_click':True
		}).status_code, 201)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		Transaction.objects.all().update(status='C') # set all to complete
		self.assertEqual(len(self.client.get('/api/orders/').data), 1)
	def test_pagination(self):
		POOLS['USD']['BTC'].add(10, 2)
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		for i in range(12):
			self.assertEqual(self.client.post('/api/orders/usd/btc/', {
				'bid_subtotal':0.001,
				'ask_subtotal':0.002,
				'withdrawal_account':btc.data['id'],
				'deposit_account':bank.data['id']
			}).status_code, 201)
		self.assertEqual(len(self.client.get('/api/transactions/').data), 10)
		self.assertEqual(len(self.client.get('/api/orders/').data), 0)
		Transaction.objects.all().update(status='C') # set all to complete
		self.assertEqual(len(self.client.get('/api/transactions/').data), 10)
		self.assertEqual(len(self.client.get('/api/orders/').data), 10)
