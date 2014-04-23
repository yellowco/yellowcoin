from binascii import unhexlify
import logging
import requests
import datetime

from django.core.exceptions import ImproperlyConfigured
from django.db import models

from django_otp.models import Device
from django_otp.oath import totp
from django_otp.util import random_hex, hex_validator

from .conf import settings

# sandbox - log files to current directory
# logging.basicConfig(filename='twilio.log',level=logging.DEBUG)

logger = logging.getLogger(__name__)
class RateLimitException(Exception):
	pass

class TwilioSMSDevice(Device):
	"""
	A :class:`~django_otp.models.Device` that delivers codes via the Twilio SMS
	service. This uses TOTP to generate temporary tokens. We use the default 30
	second time step and allow a one step grace period.

	.. attribute:: number

		*CharField*: The mobile phone number to deliver to.

	.. attribute:: key

		*CharField*: The secret key used to generate TOTP tokens.
	"""
	key = models.CharField(
		max_length=40,
		validators=[hex_validator(20)],
		default=lambda: random_hex(20),
		help_text="A random key used to generate tokens (hex-encoded)."
	)

	@property
	def last_used(self):
		return self.user.retrieve('twilio_last_used', datetime.datetime(1970, 1, 1)) 

	@last_used.setter
	def last_used(self, value):
		self.user.store('twilio_last_used', value)
		self.user.save()

	@property
	def number(self):
		return self.user.profile.payment_network.billing_address.phone

	class Meta(Device.Meta):
		verbose_name = "Twilio SMS Device"

	@property
	def bin_key(self):
		return unhexlify(self.key.encode())

	def generate_challenge(self):
		"""
		Sends the current TOTP token to ``self.number``.

		:returns: ``'Sent by SMS'`` on success.
		:raises: Exception if delivery fails.
		"""
		now = datetime.datetime.utcnow()
		if (now - self.last_used).total_seconds() < settings.OTP_TWILIO_RATE_LIMIT_INTERVAL:
			raise RateLimitException('Too many requests, ignoring...')

		token = '{0:06}'.format(totp(self.bin_key))

		# Special number for test cases
		if self.number == 5551234567:
			return token

		if settings.OTP_TWILIO_NO_DELIVERY:
			logger.info('SMS token: {0}'.format(token))
		else:
			self._deliver_token(token)
		self.last_used = now

		return "Sent by SMS"

	def _deliver_token(self, token):
		self._validate_config()

		url = 'https://api.twilio.com/2010-04-01/Accounts/{0}/SMS/Messages.json'.format(settings.OTP_TWILIO_ACCOUNT)
		data = {
			'From': settings.OTP_TWILIO_FROM,
			'To': self.number,
			'Body': 'Your Yellowcoin code is: ' + str(token),
		}

		response = requests.post(
			url, data=data,
			auth=(settings.OTP_TWILIO_ACCOUNT, settings.OTP_TWILIO_AUTH)
		)

		try:
			response.raise_for_status()
		except Exception as e:
			logger.exception('Error sending token by Twilio SMS: {0}'.format(e))
			raise

		if 'sid' not in response.json():
			message = response.json().get('message')
			logger.error('Error sending token by Twilio SMS: {0}'.format(message))
			raise Exception(message)

	def _validate_config(self):
		if settings.OTP_TWILIO_ACCOUNT is None:
			raise ImproperlyConfigured('OTP_TWILIO_ACCOUNT must be set to your Twilio account identifier')

		if settings.OTP_TWILIO_AUTH is None:
			raise ImproperlyConfigured('OTP_TWILIO_AUTH must be set to your Twilio auth token')

		if settings.OTP_TWILIO_FROM is None:
			raise ImproperlyConfigured('OTP_TWILIO_FROM must be set to one of your Twilio phone numbers')

	def verify_token(self, token):
		try:
			token = int(token)
		except Exception:
			return False
		else:
			return any(totp(self.bin_key, drift=drift) == token for drift in [0, -1])
