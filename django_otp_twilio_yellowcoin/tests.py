from django.db import IntegrityError

from django_otp.oath import totp
from django_otp.tests import TestCase


class TestTwilioSMS(TestCase):
	def setUp(self):
		try:
			self.alice = self.create_user('alice@test.com', 'password')
			self.bob = self.create_user('bob@test.com', 'password')
		except IntegrityError:
			self.skipTest("Unable to create test users.")
		else:
			self.alice.profile.payment_network.billing_address.phone = '5551234567'
			self.bob.profile.payment_network.billing_address.phone = '5551234567'
			self.alice.twiliosmsdevice_set.create(key='01234567890123456789')
			self.bob.twiliosmsdevice_set.create(key='98765432109876543210')

	def test_current(self):
		device = self.alice.twiliosmsdevice_set.get()
		token = device.generate_challenge()
		ok = device.verify_token(token)

		self.assertTrue(ok)

	def test_previous(self):
		device = self.alice.twiliosmsdevice_set.get()
		token = totp(device.bin_key, t0=30)
		ok = device.verify_token(token)

		self.assertTrue(ok)

	def test_past(self):
		device = self.alice.twiliosmsdevice_set.get()
		token = totp(device.bin_key, t0=60)
		ok = device.verify_token(token)

		self.assertTrue(not ok)

	def test_future(self):
		device = self.alice.twiliosmsdevice_set.get()
		token = totp(device.bin_key, t0=-30)
		ok = device.verify_token(token)
	
		self.assertTrue(not ok)

	def test_cross_user(self):
		device = self.alice.twiliosmsdevice_set.get()
		token = device.generate_challenge()
		ok = self.bob.twiliosmsdevice_set.get().verify_token(token)

		self.assertTrue(not ok)
