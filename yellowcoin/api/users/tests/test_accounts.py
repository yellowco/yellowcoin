from yellowcoin.api.tests import YellowcoinAPITestCase
from yellowcoin.users.models import User, PaymentMethod
from rest_framework.test import force_authenticate
from decimal import Decimal

class TestAccounts(YellowcoinAPITestCase):
	def test_credit_card(self):
		self.assertEqual(len(self.client.get('/api/accounts/credit/').data), 0)
		self.assertEqual(self.client.post('/api/accounts/bank/', {}).status_code, 400)
		response = self.create_credit_account()
		self.assertEqual(response.status_code, 201)
		self.assertEqual(self.create_credit_account().status_code, 400, "Duplicate account permitted")
		self.assertIsNotNone(response.data.get('id', None))
		self.assertTrue(response.data['card_number'].endswith('1111'))
		self.assertEqual(response.data['is_confirmed'], False)
		self.assertEqual(len(self.client.get('/api/accounts/credit/').data), 1)
		self.assertEqual(len(self.client.get('/api/accounts/').data['credit']), 1)
		response = self.client.get("/api/accounts/credit/%s/" % response.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data['card_number'].endswith('1111'))
		self.assertEqual(self.remove_credit_account(response.data['id']).status_code, 204)
		self.assertEqual(self.remove_credit_account(response.data['id']).status_code, 404)
		self.assertEqeual(len(self.client.get('/api/accounts/credit/').data), 0)

	def test_bank_account(self):
		self.assertEqual(len(self.client.get('/api/accounts/bank/').data), 0)
		self.assertEqual(self.client.post('/api/accounts/bank/', {}).status_code, 400)
		response = self.create_bank_account()
		self.assertEqual(response.status_code, 201)
		self.assertEqual(self.create_bank_account().status_code, 400, "Duplicate account permitted")
		self.assertIsNotNone(response.data.get('id', None))
		self.assertEqual(response.data['bank_name'], 'JPMORGAN CHASE BANK, NA')
		self.assertEqual(response.data['is_confirmed'], False)
		self.assertEqual(len(self.client.get('/api/accounts/bank/').data), 1)
		self.assertEqual(len(self.client.get('/api/accounts/').data['bank']), 1)
		response = self.client.get("/api/accounts/bank/%s/" % response.data['id'])
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['account_number'], 'XXXXX7890')
		self.assertEqual(self.remove_bank_account(response.data['id']).status_code, 204)
		self.assertEqual(self.remove_bank_account(response.data['id']).status_code, 404)
		self.assertEqual(len(self.client.get('/api/accounts/bank/').data), 0)

	def test_verify_bank_account(self):
		id = self.create_bank_account().data['id']
		self.assertEqual(self.client.get("/api/accounts/bank/%s/verify/" % id).status_code, 405)
		# cf. Balanced's API on bank account verification for details
		self.assertEqual(self.client.put("/api/accounts/bank/%s/verify/" % id, {
			'micropayment_1':Decimal('0.99'),
			'micropayment_2':Decimal('0.99')
		}).status_code, 400)
		self.assertEqual(self.verify_bank_account(id).status_code, 200)
		self.remove_bank_account(id)

	def test_permanent_fail_verify_bank_account(self):
		id = self.create_bank_account().data['id']
		for i in range(3):
			# cf. Balanced's API on bank account verification for details
			self.assertGreaterEqual(self.client.put("/api/accounts/bank/%s/verify/" % id, {
				'micropayment_1':99,
				'micropayment_2':99
			}).status_code, 400)
		self.assertEqual(self.verify_bank_account(id).status_code, 403, "Site vulnerable to brute force attack!")

	def test_crypto_account(self):
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 0)
		self.assertEqual(self.create_btc_account('not a real address').status_code, 400)
		self.assertEqual(self.create_btc_account().status_code, 201)
		self.assertEqual(self.create_btc_account().status_code, 400)
		response = self.client.get('/api/accounts/btc/')
		self.assertEqual(len(response.data), 1)
		self.assertEqual(len(self.client.get('/api/accounts/').data['BTC']), 1)
		self.assertEqual(self.remove_btc_account(response.data[0]['id']).status_code, 204)
		self.assertEqual(self.remove_btc_account(response.data[0]['id']).status_code, 404)
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 0)

	def test_account_default(self):
		btc = self.create_btc_account()
		self.assertTrue(self.client.get('/api/accounts/btc/%s/' % btc.data['id']).data['is_default'])
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 1)
		secondary_btc = self.create_btc_account(address='18R569MDiHfUjXKbCcUpKfN3UQpT1uhfjh')
		self.assertEqual(secondary_btc.status_code, 201)
		self.assertFalse(self.client.get('/api/accounts/btc/%s/' % secondary_btc.data['id']).data['is_default'])
		self.assertEqual(self.client.put('/api/accounts/btc/%s/' % secondary_btc.data['id'], {'is_default':True}).status_code, 200)
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 2)
		self.assertTrue(self.client.get('/api/accounts/btc/%s/' % secondary_btc.data['id']).data['is_default'])
		self.assertFalse(self.client.get('/api/accounts/btc/%s/' % btc.data['id']).data['is_default'])
		tertiary_btc = self.create_btc_account(address='19u2qKTAMNi3tk57vmfjya2MEaqKdM5k4T', is_default=True)
		self.assertEqual(tertiary_btc.status_code, 201)
		self.assertFalse(self.client.get('/api/accounts/btc/%s/' % secondary_btc.data['id']).data['is_default'])
		self.assertFalse(self.client.get('/api/accounts/btc/%s/' % btc.data['id']).data['is_default'])
		self.assertTrue(self.client.get('/api/accounts/btc/%s/' % tertiary_btc.data['id']).data['is_default'])

	def test_account_crossover(self):
		bank = self.create_bank_account()
		credit = self.create_credit_account()
		btc = self.create_btc_account()
		self.assertEqual(len(self.client.get('/api/accounts/bank/').data), 1)
		self.assertEqual(len(self.client.get('/api/accounts/credit/').data), 1)
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 1)
		
		secondary = self.create_user('test2@test.com', 'test')
		self.client.logout()
		self.assertTrue(self.client.login(username='test2@test.com', password='test'))
		self.assertEqual(len(self.client.get('/api/accounts/bank/').data), 0)
		self.assertEqual(len(self.client.get('/api/accounts/credit/').data), 0)
		self.assertEqual(len(self.client.get('/api/accounts/btc/').data), 0)
		self.assertEqual(self.client.get("/api/accounts/bank/%s/" % bank.data['id']).status_code, 404)
		self.assertEqual(self.client.get("/api/accounts/credit/%s/" % credit.data['id']).status_code, 404)
		self.assertEqual(self.client.get("/api/accounts/btc/%s/" % btc.data['id']).status_code, 404)
		self.assertEqual(self.client.put("/api/accounts/bank/%s/verify/" % bank.data['id']).status_code, 404)
		secondary.profile.payment_network.delete() # clean up a bit
