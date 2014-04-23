from yellowcoin.api.tests import YellowcoinAPITestCase
from decimal import Decimal

class TestRecurringOrders(YellowcoinAPITestCase):
	def test_recurring_orders(self):
		bank = self.create_bank_account()
		btc = self.create_btc_account()
		self.verify_bank_account(bank.data['id'])
		template = self.create_order_template(bank.data['id'], btc.data['id'])
		self.assertEqual(template.status_code, 201)
		self.assertEqual(len(self.client.get('/api/orders/recurring/').data), 0)
		response = self.client.post('/api/orders/recurring/', {
			'template':template.data['id'],
			'interval':100,
			'first_run':'2014-01-25T10:32:02Z'
		})
		self.assertEqual(response.status_code, 201, response)
		self.assertIsNotNone(response.data['id'])
		self.assertEqual(self.client.get("/api/orders/recurring/%s/" % response.data['id']).status_code, 200)
		self.assertIsNotNone(self.client.get("/api/orders/recurring/%s/" % response.data['template']['id']))
		self.assertEqual(len(self.client.get('/api/orders/recurring/').data), 1)
		self.assertEqual(self.client.delete("/api/orders/recurring/%s/" % response.data['id']).status_code, 204)
		self.assertEqual(self.client.get("/api/orders/recurring/%s/" % response.data['id']).status_code, 404)
		response = self.client.post('/api/orders/recurring/', {
			'template':template.data['id'],
			'interval':100,
			'first_run':'2014-01-25T10:32:02Z'
		})
		self.assertEqual(response.status_code, 201)
		self.assertEqual(self.client.delete("/api/orders/templates/%s/" % template.data['id']).status_code, 204)
		self.assertEqual(self.client.get("/api/orders/recurring/%s/" % response.data['id']).status_code, 404)
