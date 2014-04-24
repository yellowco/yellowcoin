from rest_framework.test import APIRequestFactory
from rest_framework.test import APITestCase, APIClient
from yellowcoin.users.models import User, PaymentMethod
from django.conf import settings
from balanced_yellowcoin import balanced
from decimal import Decimal

class YellowcoinAPITestCase(APITestCase):
	def setUp(self):
		self.base_user = self.create_user('test@test.com', 'test')
		self.factory = APIRequestFactory()
		self.client = APIClient()
		self.client.login(email='test@test.com', password='test')

	def tearDown(self):
		self.base_user.profile.payment_network.delete() # clean up a bit
		self.client.logout()

	def create_user(self, username, password='test'):
		user = User.objects.create_user(username, password)
		user.save()
		return user
	
	def create_bank_account(self):
		# create an account
		return self.client.post('/api/accounts/bank/', {
			'first_name':'Testy','last_name':'McTesterson',
			'routing_number':'072000326','account_number':'1234567890',
			'type':'checking'
		})

	def remove_bank_account(self, id):
		return self.client.delete("/api/accounts/bank/%s/" % id)

	def verify_bank_account(self, id):
		# report values in cents
		# test accounts have validation values of $0.01 and $0.01
		#	cf. http://bit.ly/P9ZkX7
		return self.client.put("/api/accounts/bank/%s/verify/" % id, {
			'micropayment_1':Decimal('0.01'),
			'micropayment_2':Decimal('0.01')
		})
		
	def create_btc_account(self, address='15AeuxTuPQpntVvq4KVGqSxZM3ry39PV6Q', is_default=False):
		return self.client.post('/api/accounts/btc/', {'address':address, 'is_default':is_default})

	def remove_btc_account(self, id):
		return self.client.delete("/api/accounts/btc/%s/" % id)

	def create_order_template(self, bank_id, btc_id):
		return self.client.post('/api/orders/templates/btc/usd/', {
			'withdrawal_account':bank_id,
			'deposit_account':btc_id,
			'type':'ask',
			'subtotal':0.05
		})

	def remove_order_template(self, id):
		return self.client.delete("/api/orders/templates/%s/" % id)

	def create_order(self, bank_id, btc_id):
		return self.client.post('/api/orders/btc/usd/', {
			'bid_subtotal':0.1,
			'ask_subtotal':0.05,
			'withdrawal_account':bank_id,
			'deposit_account':btc_id
		})
