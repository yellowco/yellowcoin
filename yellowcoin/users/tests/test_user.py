from bitcoind_emulator import EmulatedBitcoinConnection
from django.test import TestCase
from django.test.client import Client
from django.conf import settings
from django.test.utils import override_settings
from yellowcoin.users.models import User, EmailValidation, APIKey, CryptoAccount
from yellowcoin.users.signals import referral_completed
from django.contrib.gis.geoip import GeoIP

@override_settings(BTC_CONN=EmulatedBitcoinConnection())
class TestUser(TestCase):
	def setUp(self):
		self.user = User.objects.create_user('test@test.com','test')
	
	def test_login(self):
		self.assertEqual(self.user.login_records.count(), 0)
		response = self.client.post('/users/login/', {'username':'nope@test.com', 'password':'wrong'})
		self.assertEqual(response.status_code, 400)
		response = self.client.post('/users/login/', {'username':'nope@test.com', 'password':'test'})
		self.assertEqual(response.status_code, 400)
		response = self.client.post('/users/login/', {'username':'test@test.com', 'password':'wrong'})
		self.assertEqual(response.status_code, 400)
		response = self.client.post('/users/login/', {'username':'test@test.com', 'password':'test'})
		self.assertEqual(response.status_code, 302) # redirects
		self.assertEqual(self.user.login_records.count(), 1)
		self.assertEqual(self.user.login_records.first().ip, '127.0.0.1')
		response = self.client.post('/users/login/', {'username':'test@test.com', 'password':'wrong'})
		self.assertEqual(response.status_code, 302) # should now redirect
		response = self.client.post('/users/login/', {'username':'test@test.com', 'password':'test'})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(self.user.login_records.count(), 1)
		response = self.client.get('/users/logout/')
		self.assertEqual(response.status_code, 302)
		response = self.client.post('/users/login/', {'username':'test@test.com', 'password':'test'})
		self.assertEqual(response.status_code, 302)
		self.assertEqual(self.user.login_records.count(), 2)
		self.assertEqual(self.user.login_records.first().ip, '127.0.0.1')
		
	def test_store_retrieve(self):
		self.assertIsNone(self.user.retrieve('test'))
		self.user.store('test', 'testData')
		self.assertEqual(self.user.retrieve('test'), 'testData')
		self.user.store('test', None)
		self.assertTrue('test' not in self.user.fingerprint)
	def test_user_unconfirmed_email(self):
		self.assertEqual(self.user.unconfirmed_email, 'test@test.com')
		self.assertIsNotNone(self.user.activation_key)
		validation = EmailValidation.objects.get(user=self.user)
		self.assertEqual(validation.email, 'test@test.com')
		validation.email = 'test2@test.com'
		validation.save()
		self.assertIsNotNone(self.user.activation_key)
		self.assertEqual(self.user.unconfirmed_email, 'test2@test.com')
		validation.delete()
		self.assertIsNone(self.user.activation_key)
		self.assertEqual(self.user.unconfirmed_email, 'test@test.com')
		self.user.unconfirmed_email = 'test3@test.com'
		self.assertEqual(self.user.email, 'test@test.com')
		self.assertEqual(self.user.unconfirmed_email, 'test3@test.com')
	def test_referral_id(self):
		self.assertIsNotNone(self.user.referral_id)
		self.assertEqual(User.objects.from_referral_id(self.user.referral_id).id, self.user.id)
		self.assertIsNone(self.user.referrer)
		self.assertIsNone(self.user.is_referrer_paid)
		second_user = User.objects.create_user('test2@test.com','test')
		self.user.referrer = second_user
		self.user.save()
		self.assertIsNone(self.user.is_referrer_paid)

		address = settings.BTC_CONN.getnewaddress()
		referral_completed.send(sender=None, user=self.user)
		self.assertEqual(settings.BTC_CONN.getreceivedbyaddress(address), 0)
		CryptoAccount.objects.create(user=second_user,
			address=address,
			currency='BTC',
			nickname='asdf',
			is_default=True
		).save()
		referral_completed.send(sender=None, user=self.user)
		self.assertIsNotNone(self.user.referrer)
		self.assertIsNotNone(self.user.referrer.crypto_accounts.get(currency='BTC', is_default=True))
		self.assertEqual(settings.BTC_CONN.getreceivedbyaddress(address), settings.REFERRAL_BONUS)
		self.assertIsNotNone(self.user.is_referrer_paid)
		referral_completed.send(sender=None, user=self.user)
		self.assertEqual(settings.BTC_CONN.getreceivedbyaddress(address), settings.REFERRAL_BONUS)
		self.assertIsNotNone(self.user.is_referrer_paid)
		second_user.profile.payment_network.delete()
		
	def test_api_key(self):
		APIKey.objects.create(user=self.user, comment='test').save()
		self.assertEqual(APIKey.objects.filter(user=self.user).count(), 1)
		api_key = APIKey.objects.get(user=self.user)
		self.assertIsNotNone('/api/settings/?key=%s' % api_key.key)
		self.assertEqual(Client().get('/api/settings/').status_code, 403)
		self.assertEqual(Client().get('/api/settings/?key=%s' % api_key.key).status_code, 403) # api not enabled
		self.user.use_api = True
		self.user.save()
		self.assertEqual(Client().get('/api/settings/?key=%s' % api_key.key).status_code, 200)
	def test_geolocation(self):
		# just check if geoip is functioning
		try:
			self.assertIsNotNone(GeoIP().city('72.14.207.99'))
		except:
			self.fail("Please run `aptitude install geoip-database-contrib`")
		
