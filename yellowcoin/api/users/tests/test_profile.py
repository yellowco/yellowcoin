from yellowcoin.api.tests import YellowcoinAPITestCase
from yellowcoin.users.models import User, EmailValidation

class TestProfile(YellowcoinAPITestCase):
	def test_get_profile(self):
		response = self.client.get('/api/profile/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['email'], self.base_user.email)
		self.assertEqual(response.data['first_name'], None)
		self.assertEqual(response.data['last_name'], None)
		self.assertEqual(response.data['is_valid']['phone'], False)
	def test_restrict_profile(self):
		self.assertEqual(self.client.post('/api/profile/', {}).status_code, 405)
		self.assertEqual(self.client.delete('/api/profile/', {}).status_code, 405)
		self.client.logout()
		self.assertEqual(self.client.get('/api/profile/').status_code, 403)
		self.assertEqual(self.client.put('/api/profile/').status_code, 403)
	def test_set_phone(self):
		self.base_user.profile.valid_phone = True
		self.base_user.profile.save()
		response = self.client.get('/api/profile/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['is_valid']['phone'], True)
		response = self.client.put('/api/profile/', {'phone':7731234567, 'current_password':'test'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['phone'], u'773-123-4567')
		self.assertEqual(response.data['is_valid']['phone'], False)
	def test_set_email(self):
		response = self.client.get('/api/profile/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['is_valid']['email'], False)
		self.assertEqual(EmailValidation.objects.filter(user=self.base_user).count(), 1)
		EmailValidation.objects.filter(user=self.base_user).delete()
		response = self.client.get('/api/profile/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['is_valid']['email'], True)
		response = self.client.put('/api/profile/', {'email':'test2@test.com', 'current_password':'test'})
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['email'], 'test2@test.com')
		self.assertEqual(response.data['is_valid']['email'], False)

	def test_change_password(self):
		response = self.client.put('/api/profile/', {'current_password':'test', 'password':'test2'})
		self.assertEqual(response.status_code, 200)
		self.client.logout()
		self.assertFalse(self.client.login(email='test@test.com', password='test'))
		self.assertTrue(self.client.login(email='test@test.com', password='test2'))
		
	def test_valid_bank(self):
		bank = self.create_bank_account()
		response = self.client.get('/api/profile/')
		self.assertEqual(response.data['is_valid']['bank_account'], False)
		self.verify_bank_account(bank.data['id'])
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['bank_account'], True)
		self.client.delete('/api/accounts/bank/%s/' % bank.data['id'])
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['bank_account'], False)

	def test_identity_verify(self):
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['profile'], False)
		request = self.client.put('/api/profile/', {
			'current_password':'test',
			'first_name':'Testy',
			'last_name':'McTesterson',
			'address1':'123 Jump Street',
			'city':'Chicago',
			'state':'IL',
			'zip':'60637',
			'dob':'1991-01-01',
			'ssn':'0001'})
		self.assertEqual(request.status_code, 400, request.data)
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['profile'], False)
		self.assertEqual(self.client.put('/api/profile/', {
			'current_password':'test',
			'first_name':'Testy',
			'last_name':'McTesterson',
			'address1':'123 Jump Street',
			'city':'Chicago',
			'state':'IL',
			'zip':'60637',
			'dob':'1991-01-01',
			'ssn':'0000'}).status_code, 200, request.data)
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['profile'], True)
		self.assertEqual(self.client.put('/api/profile/', {
			'current_password':'test',
			'first_name':'Testy',
			'last_name':'McTesterson',
			'address1':'123 Jump Street',
			'city':'Chicago',
			'state':'IL',
			'zip':'60637',
			'dob':'1991-01-01',
			'ssn':'0000'}).status_code, 400, request.data)
		self.assertEqual(self.client.get('/api/profile/').data['is_valid']['profile'], True)
	def test_identity_verify_too_many_tries(self):
		for i in range(3):
			request = self.client.put('/api/profile/', {
				'current_password':'test',
				'first_name':'Testy',
				'last_name':'McTesterson',
				'address1':'123 Jump Street',
				'city':'Chicago',
				'state':'IL',
				'zip':'60637',
				'dob':'1991-01-01',
				'ssn':'0001'})
			self.assertEqual(request.status_code, 400, "Failed on attempt %d" % (i + 1))
		request = self.client.put('/api/profile/', {
			'current_password':'test',
			'first_name':'Testy',
			'last_name':'McTesterson',
			'address1':'123 Jump Street',
			'city':'Chicago',
			'state':'IL',
			'zip':'60637',
			'dob':'1991-01-01',
			'ssn':'0001'})
		self.assertEqual(request.status_code, 403, request.data)
