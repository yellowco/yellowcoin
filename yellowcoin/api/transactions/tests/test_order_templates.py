from yellowcoin.api.tests import YellowcoinAPITestCase
from decimal import Decimal

class TestOrderTemplates(YellowcoinAPITestCase):
	def test_order_templates(self):
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 0)
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.assertEqual(self.create_order_template(bank.data['id'], btc.data['id']).status_code, 400) # verify can't add to invalid bank account
		self.assertEqual(self.create_order_template(bank.data['id'], bank.data['id']).status_code, 400) 
		self.assertEqual(self.create_order_template(btc.data['id'], btc.data['id']).status_code, 400) 
		self.verify_bank_account(bank.data['id'])
		self.assertEqual(self.client.post('/api/orders/templates/btc/usd/', {
			'withdrawal_account':bank.data['id'],
			'deposit_account':btc.data['id'],
			'type':'A'
		}).status_code, 400)
		template = self.create_order_template(bank.data['id'], btc.data['id'])
		self.assertEqual(template.status_code, 201, template)
		response = self.client.get('/api/orders/templates/')
		self.assertEqual(len(response.data), 1)
		self.assertEqual(len(self.client.get('/api/orders/templates/btc/usd/').data), 1)
		self.assertEqual(len(self.client.get('/api/orders/templates/usd/btc/').data), 0)
		self.assertIsNotNone(response.data[0]['id'])
		self.assertEqual(response.data[0]['withdrawal_account'], bank.data['id'])
		self.assertEqual(response.data[0]['deposit_account'], btc.data['id'])
		self.assertEqual(response.data[0]['type'], 'A')
		self.assertEqual(response.data[0]['subtotal'], Decimal('0.05'))
		self.assertEqual(self.client.patch("/api/orders/templates/%s/" % response.data[0]['id'], {
			'subtotal':0.06
		}).status_code, 200)
		self.assertEqual(self.client.get('/api/orders/templates/').data[0]['subtotal'], Decimal('0.06'))
		self.assertEqual(self.remove_order_template(response.data[0]['id']).status_code, 204)
		self.assertEqual(self.remove_order_template(response.data[0]['id']).status_code, 404)
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 0)
	
	def test_settings_template_population(self):
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 0)
		self.assertIsNotNone(self.client.get('/api/settings/').data['one_click_order_template']['id'])
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 1)

	def test_template_crossover(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		template = self.create_order_template(bank.data['id'], btc.data['id'])
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 1)
		self.client.logout()
		secondary = self.create_user('test2@test.com')
		self.assertTrue(self.client.login(username='test2@test.com', password='test'))
		self.assertEqual(len(self.client.get('/api/orders/templates/').data), 0)
		self.assertEqual(self.client.get('/api/orders/templates/%s/' % template.data['id']).status_code, 404)
		secondary.profile.payment_network.delete() # clean up a bit
