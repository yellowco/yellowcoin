from yellowcoin.api.tests import YellowcoinAPITestCase
from yellowcoin.users.models import User

class TestSettings(YellowcoinAPITestCase):
	def test_get_put_settings(self):
		response = self.client.get('/api/settings/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['two_factor_authentication'], False)
		self.assertEqual(response.data['one_click'], False)
		self.assertIsNotNone(response.data['one_click_order_template']['id'])
		response = self.client.put('/api/settings/',{'two_factor_authentication':True})
		self.assertEqual(response.status_code, 400) # phone number not validated
		response = self.client.put('/api/settings/',{'one_click':True})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['one_click'], True)
	def test_restrict_settings(self):
		self.assertEqual(self.client.post('/api/settings/', {}).status_code, 405)
		self.assertEqual(self.client.delete('/api/settings/', {}).status_code, 405)
		self.client.logout()
		self.assertEqual(self.client.get('/api/settings/').status_code, 403)
		self.assertEqual(self.client.put('/api/settings/').status_code, 403)
	def test_settings_crossover(self):
		response = self.client.get('/api/settings/').data
		self.client.logout()
		secondary = self.create_user('test2@test.com')
		self.client.login(username='test2@test.com', password='test')
		secondary_response = self.client.get('/api/settings/').data
		self.assertNotEqual(response['one_click_order_template']['id'], secondary_response['one_click_order_template']['id'])
		secondary.profile.payment_network.delete() # clean up a bit
