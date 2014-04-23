from django.test import TestCase
from django.test.client import Client
from yellowcoin.users.models import User, EmailValidation, APIKey
from yellowcoin.users import signals

class SignalTestCase(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('test@test.com','test')

	def failure_signal(self, *args, **kwargs):
		pass

	def test_login_signal(self):
		signals.login.send = self.failure_signal
		self.client.post('/users/login/', {'username':'test@test.com', 'password':'test'})
		
