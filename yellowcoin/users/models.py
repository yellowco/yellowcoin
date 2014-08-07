from django.utils import timezone
from django.db import models, transaction
from django.conf import settings
from django.dispatch import receiver
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import *
from django.db import IntegrityError
from base64 import urlsafe_b64encode, urlsafe_b64decode
from random import random
from hashlib import sha256, sha1
from picklefield.fields import PickledObjectField
from datetime import timedelta
from yellowcoin import crypto
from yellowcoin.api.exceptions import LockedError, BankValidationError
from django_routing_numbers import Institution
import requests
import re
import phonenumbers
from decimal import Decimal
from Crypto.Cipher import AES
from Crypto import Random
from balanced_yellowcoin import balanced as payment_network
from django.contrib.gis.geoip import GeoIP

import bitcoinrpc
from bitcoinrpc.exceptions import InsufficientFunds
from yellowcoin.api.exceptions import InsufficientFundsException

from yellowcoin.enums import CRYPTOCURRENCIES, CURRENCIES

class UserManager(BaseUserManager):
	def create_user(self, email, password):
		"""
		Create and save a User with the given email and password
		"""
		user = self.model(email=email.lower())
		user.set_password(password)
		user.save(using=self._db)
		user.unconfirmed_email = email.lower()
		Profile.objects.create(user=user, payment_network_id=None).save()
		return user

	def create_superuser(self, email, password):
		"""
		Create and save a superuser with the given email and password, automatically activated
		"""
		user = self.model(email=email.lower())
		user.set_password(password)
		user.is_active = True
		user.is_staff = True
		user.is_superuser = True
		user.save(using=self._db)
		return user
	
	def from_referral_id(self, value):
		if isinstance(value, unicode):
			value = value.encode("UTF-8")
		try:
			data = urlsafe_b64decode(value)
			iv = settings.SECRET_KEY[-16:]
			cipher = AES.new(settings.SECRET_KEY[:32], AES.MODE_CBC, iv)
			return self.get(id=cipher.decrypt(data).rstrip(b'\0')[:-16])
		except:
			return None


class User(AbstractBaseUser, PermissionsMixin):
	class Meta:
		ordering = ['id']

	email = models.EmailField(max_length=254, unique=True, db_index=True)
	USERNAME_FIELD ='email'

	# should be used to verify email - users should still need to log in in the meantime
	is_active = models.BooleanField(default=True, help_text='Designates whether or not the user account has been disabled')
	is_staff = models.BooleanField(default=False)

	date_joined = models.DateTimeField(auto_now_add=True)
	fingerprint = PickledObjectField()

	use_2fa = models.BooleanField(default=False)
	use_api = models.BooleanField(default=False)

	# if there was a referral from an existing user, note this
	# User.referrals returns a list of all referred users
	is_referrer_paid = models.CharField(max_length=64, null=True)
	referrer = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='referred_set', null=True)

	def store(self, key, value):
		if not self.fingerprint or len(self.fingerprint) == 0:
			self.fingerprint = {}
		if value is not None:
			self.fingerprint[key] = value
		else:	# no sense in storing it...
			self.fingerprint.pop(key)

	def retrieve(self, key, default=None):
		if not self.fingerprint or len(self.fingerprint) == 0:
			self.fingerprint = {}
		return self.fingerprint[key] if key in self.fingerprint else default

	@property
	def unconfirmed_email(self):
		try:
			return EmailValidation.objects.get(user=self).email
		except:
			return self.email

	@unconfirmed_email.setter
	def unconfirmed_email(self, value):
		try:
			EmailValidation.objects.get(user=self).delete()
		except:
			EmailValidation.objects.create(user=self, email=value, key=crypto.gen_random_hash()).save()

	@property
	def activation_key(self):
		try:
			return EmailValidation.objects.get(user=self).key
		except:
			return None

	@property
	def use_one_click(self):
		return self.retrieve('use_one_click', False)
	
	@use_one_click.setter
	def use_one_click(self, value):
		return self.store('use_one_click', value)

	@property
	def one_click_order_template(self):
		from yellowcoin.transactions.models import OrderTemplate
		id = self.retrieve('one_click_order_template')
		template = None
		try:
			template = OrderTemplate.objects.get(id=id)
		except OrderTemplate.DoesNotExist:
			pass
		if template is None:
			template = OrderTemplate.objects.create(user=self, type='A', subtotal=0)
			template.save()
			self.store('one_click_order_template', template.id)
			self.save()
		return template


	@property
	def referral_id(self):
		def pad(s):
			return s + b'\0' * (AES.block_size - len(s) % AES.block_size)
		message = pad(str(self.id) + settings.SECRET_KEY[:16])
		iv = settings.SECRET_KEY[-16:]
		cipher = AES.new(settings.SECRET_KEY[:32], AES.MODE_CBC, iv)
		return urlsafe_b64encode(cipher.encrypt(message))

	def __unicode__(self):
		return self.email

	def get_full_name(self):
		return self.get_username()
	
	def get_short_name(self):
		return self.get_username()

	def is_authenticated(self):
		return super(User, self).is_authenticated() and (not self.use_2fa or not self.profile.valid_phone or self.is_verified())

	def get_limit(self, currency):
		if currency == 'BTC':
			if self.profile.valid_profile and self.profile.valid_transaction:
				return Decimal('1')
			if self.profile.valid_profile:
				return Decimal('0.5')
			if self.profile.valid_phone:
				return Decimal('0.25')
			if self.profile.valid_bank_account:
				return Decimal('0.1')
			return Decimal('0.0')
		return Decimal('2147483647')

	def get_all_limits(self):
		data = {}
		db = self.transaction_limits.all()
		currencies = CRYPTOCURRENCIES + CURRENCIES
		for (currency, name) in currencies.items():
			data[currency] = {
				'cur_amount':"0",
				'max_amount':self.get_limit(currency)
			}
			for override in db:
				if override.currency == currency:
					data[currency] = {
						'cur_amount':override.cur_amount,
						'max_amount':override.max_amount
					}
					break
		return data


	@property
	def bank_accounts(self):
		# reserved for future expansion
		return self.profile.payment_network.bank_accounts

	objects = UserManager()

class Record(models.Model):
	class Meta:
		abstract = True
		ordering = ['-timestamp']

	ip = models.GenericIPAddressField()
	timestamp = models.DateTimeField(auto_now_add=True)
	content = PickledObjectField()

	def store(self, key, value):
		if not self.content or len(self.content) == 0:
			self.content = {}
		if value is not None:
			self.content[key] = value
		else:	# no sense in storing it...
			self.content.pop(key)

	def retrieve(self, key, default=None):
		if not self.content or len(self.content) == 0:
			self.content = {}
		return self.content[key] if key in self.content else default

	@property
	def location(self):
		try:
			location = GeoIP().city(str(self.ip))
			if location['country_name']:
				if location['city']:
					return "%s, %s" % (location['city'], location['country_name'])
				else:
					return location['country_name']
			elif location['city']:
				return location['city']
		except:
			pass
		return 'Unknown'

class WaitlistRecord(Record):
	pass # lol

class ResetRecord(Record):
	id = models.CharField(max_length=16, default=crypto.gen_eid, primary_key=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='reset_records')
	is_valid = models.BooleanField(default=True)
	type = models.CharField(max_length=2, choices=(('PW', 'password'), ('PH', 'phone')), default='PW')

class LoginRecord(Record):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='login_records')
	is_successful = models.BooleanField(default=False)

	def __init__(self, *args, **kwargs):
		super(LoginRecord, self).__init__(*args, **kwargs)

	def save(self, *args, **kwargs):
		# limit ten records
		super(LoginRecord, self).save(*args, **kwargs)
		user_records = LoginRecord.objects.filter(user=self.user)
		if user_records.count() > 10:
			user_records.last().delete()

class Profile(models.Model):
	class Meta:
		ordering = ['user__id']

	user = models.OneToOneField(settings.AUTH_USER_MODEL)
	payment_network_id = models.CharField(max_length=64, null=True)
	valid_profile = models.BooleanField(default=False)
	valid_phone = models.BooleanField(default=False)
	retries_remaining = models.IntegerField(default=4)

	@property
	def valid_email(self):
		return EmailValidation.objects.filter(user=self.user).count() == 0

	@property
	def valid_transaction(self):
		return self.user.transactions.filter(status='C').count() > 0

	@property
	def valid_bank_account(self):
		return sum([BankAccount(x).can_debit  for x in self.payment_network.bank_accounts]) > 0

	def __unicode__(self):
		return self.user.get_username()

	@models.permalink
	def get_absolute_url(self):
		return ['users|account']

	def update(self, attrs):
		updated = set()
		for key, value in attrs.items():
			for token in key.split('.'):
				updated.add(token)
			if value == '':
				value = None # edge case
			setattr(reduce(getattr, key.split('.')[:-1], self), key.split('.')[-1], value)
			if key == 'payment_network.billing_address.phone':
				self.valid_phone = False
				self.save()
				self.user.use_2fa = False
				self.user.save()

		# verify user via blockscore.com
		# check profile delta -- if changes exist and the profile has not yet been validated, then validate and set profile.valid_profile
		#	cf. http://bit.ly/1kET9rZ
		validated_profile = self.valid_profile
		raise_profile_validation_error = False

		if 'payment_network' in updated:
			# it's possible that first/last name were updated, so those fields should be saved too
			self.payment_network.save()

		if ('gender' in updated or 'dob' in updated or 'passport' in updated or 'ssn' in updated) and (not validated_profile):
			if self.retries_remaining > 0:
				self.valid_profile = self.verify()
				self.retries_remaining -= (not self.valid_profile)
				validated_profile = True
				self.save()
			else:
				raise_profile_validation_error = True

		if 'user' in updated:
			self.user.save()

	def save(self, *args, **kwargs):
		try:
			existing_profile = Profile.objects.get(user=self.user)
			self.id = existing_profile.id
		except Profile.DoesNotExist:
			pass
		if (self.valid_profile == None):
			self.valid_profile = False
		super(Profile, self).save(*args, **kwargs)

	@property
	def phone(self):
		return self.payment_network.billing_address.phone

	@phone.setter
	def phone(self, value):
		self.payment_network.billing_address.phone = value

	@property
	def first_name(self):
		return self.payment_network.billing_address.first_name
	
	@first_name.setter
	def first_name(self, value):
		self.payment_network.billing_address.first_name = value

	@property
	def last_name(self):
		return self.payment_network.billing_address.last_name

	@last_name.setter
	def last_name(self, value):
		self.payment_network.billing_address.last_name = value

	# ID verify only for US-local addresses
	@property
	def country_code(self):
		return 'US'

	@property
	def passport(self):
		return self.blockscore['passport']

	@property
	def gender(self):
		return self.blockscore['gender']

	@property
	def dob(self):
		if self.blockscore['dob']:
			return self.blockscore['dob'].strftime('%Y-%m-%d')
		return self.blockscore['dob']

	@passport.setter
	def passport(self, value):
		self.blockscore['passport'] = value

	@gender.setter
	def gender(self, value):
		self.blockscore['gender'] = value

	@dob.setter
	def dob(self, value):
		self.blockscore['dob'] = value

	# TODO -- Kevin, update balanced to save this instead
	@property
	def ssn(self):
		return self.blockscore['ssn']

	@ssn.setter
	def ssn(self, value):
		self.blockscore['ssn'] = value

	@property
	def blockscore(self):
		if not hasattr(self, '_blockscore'):
			self._blockscore = {
				'dob' : '',
				'gender' : '',
				'passport' : '',
				'ssn':''
			}
		return self._blockscore

	@property
	def payment_network(self):
		if not hasattr(self, '_payment_network'):
			if not self.payment_network_id:
				client = payment_network.Client.create(email=self.user.email)
				self.payment_network_id = client.save().id
				self.save()
				self._payment_network = Client(client=client)
			elif self.payment_network_id in Client.CACHE:
				self._payment_network = Client.CACHE[self.payment_network_id]
			else:
				self._payment_network = Client(id=self.payment_network_id)
		return self._payment_network

	@payment_network.setter
	def payment_network(self, value):
		self.payment_network_id = value.id

	def verify(self):
		type = 'us_citizen' if self.country_code == 'US' else 'international_citizen'
		id_type = 'ssn' if type == 'us_citizen' else 'passport'
		id_data = self.ssn if id_type == 'ssn' else self.passport
		headers = { 'Accept' : 'application/vnd.blockscore+json;version=2', }
		payload = {
			'type' : type,
			'identification[%s]' % (id_type) : id_data,
			'date_of_birth' : self.dob,
			'name[first]' : self.payment_network.billing_address.first_name,
			'name[middle]' : '',
			'name[last]' : self.payment_network.billing_address.last_name,
			'address[city]' : self.payment_network.billing_address.city,
			'address[street1]' : self.payment_network.billing_address.street1,
			'address[street2]' : self.payment_network.billing_address.street2,
			'address[state]' : self.payment_network.billing_address.state,
			'address[postal_code]' : self.payment_network.billing_address.postal,
			'address[country_code]' : self.country_code,
		}
		if type == 'international_citizen':
			payload['gender'] = self.gender

		resp = requests.post(settings.BLOCKSCORE_API_URL, data=payload, headers=headers, auth=(settings.BLOCKSCORE_API_KEY, ''), )
		# the response is parsed as per http://bit.ly/1kET9rZ
		if resp.status_code == 201:
			return resp.json()['status'] == 'valid'

class EmailValidation(models.Model):
	user = models.OneToOneField(settings.AUTH_USER_MODEL)
	email = models.EmailField()
	key = models.CharField(max_length=64)

class Client(object):
	CACHE = {} # Querying payment_network is slow. TURBO CHARGE IT.
	def __init__(self, client=None, id=None):
		if client is None and id is None:
			raise AttributeError('Either client or id must be set')
		if settings.CACHE:
			Client.CACHE[id if id is not None else client.id] = self
		self._id_verify = None
		self._ci = id
		self._c = client

	@property
	def billing_address(self):
		self._check_client_loaded()
		ba = self._c.billing_address
		if ba.phone != '' and ba.phone:
			try:
				ba.phone = phonenumbers.parse(ba.phone, 'US').national_number
			except:
				pass
		return ba

	def verify(self):
		if not self._id_verify:
			self.__dict__['_id_verify'] = self._c.verify()
		return self._id_verify

	# TODO - if phone not valid, do not set use_2fa = True
	def save(self):
		# hijack the save
		self._check_client_loaded()
		try:
			phone = phonenumbers.parse(self._c.billing_address.phone, 'US')
			self._c.billing_address.phone = phonenumbers.format_number(phone, phonenumbers.PhoneNumber())
		except:
			self._c.billing_address.phone = None
		# remove it from cache
		return self._c.save()

	def __getattr__(self, name):
		self._check_client_loaded()
		return getattr(self._c, name)

	def __setattr__(self, name, value):
		if '_c' not in self.__dict__ or name == '_c':
			self.__dict__[name] = value
		else:
			self.__dict__['_id_verify'] = None # reset id verify
			self._check_client_loaded()
			setattr(self._c, name, value)

	def _check_client_loaded(self):
		if self._c is None:
			self._c = payment_network.Client.retrieve(id=self._ci)
			if self._c is None:
				raise KeyError('id not found on payment network')

	def __iter__(self):
		yield self
	
	@property
	def bank_accounts(self):
		self._check_client_loaded()
		return [BankAccount(x) for x in filter(
				lambda y: isinstance(y, payment_network.BankAccount), self.payment_methods)]

	def __str__(self):
		self._check_client_loaded()
		return str(self._c)

class CreditCard(object):
	class DoesNotExist(Exception):
		pass

	@property
	def is_locked(self):
		return PaymentMethod.objects.get(id=self.eid).is_locked

	def __init__(self, account):
		self._account = account
	def __getattr__(self, name):
		try:
			return getattr(self._account, name)
		except:
			return None # because possible key errors
	def __setattr__(self, name, value):
		if '_account' not in self.__dict__:
			self.__dict__[name] = value
		else:
			setattr(self._account, name, value)
	def __iter__(self):
		yield self

	def __str__(self):
		return str(self._account)

	def delete(self):
		if self.is_locked:
			raise LockedError()
		try:
			PaymentMethod.objects.get(foreign_model='D', foreign_key=self.id).delete()
		except PaymentMethod.DoesNotExist:
			pass
		return self._account.delete()

	@property
	def card_type(self):
		return self.type

	@staticmethod
	def retrieve(id, **kwargs):
		account = payment_network.CreditCard.retrieve(id, **kwargs)
		if not account:
			raise CreditCard.DoesNotExist()
		return account

	@property
	def eid(self):
		return PaymentMethod.get_id(foreign_model='D', foreign_key=self.id)

	@property
	def first_name(self):
		return self.account_holder.split(' ')[0]

	@property
	def last_name(self):
		return ' '.join(self.account_holder.split(' ')[1:])

	# TODO - generalize this
	# currencies accepted by the credit / debit card
	@property
	def send(self):
		return ( 'USD', )
	@property
	def recv(self):
		return ( 'USD', )

# Don't bother lazy-loading the bankaccount object.
# There's no child objects and almost every operation requires data in the db.
class BankAccount(object):
	class DoesNotExist(Exception):
		pass

	@property
	def is_locked(self):
		return PaymentMethod.objects.get(id=self.eid).is_locked

	def __init__(self, account):
		self._account = account
	def __getattr__(self, name):
		try:
			return getattr(self._account, name)
		except:
			return None # because possible key errors
	def __setattr__(self, name, value):
		if '_account' not in self.__dict__:
			self.__dict__[name] = value
		else:
			setattr(self._account, name, value)
	def __iter__(self):
		yield self

	def __str__(self):
		return str(self._account)

	def delete(self):
		if self.is_locked:
			raise LockedError()
		try:
			PaymentMethod.objects.get(foreign_model='C', foreign_key=self.id).delete()
		except PaymentMethod.DoesNotExist:
			pass
		return self._account.delete()

	@staticmethod
	def retrieve(id, **kwargs):
		account = payment_network.BankAccount.retrieve(id, **kwargs)
		if not account:
			raise BankAccount.DoesNotExist()
		return account

	@property
	def eid(self):
		return PaymentMethod.get_id(foreign_model='P', foreign_key=self.id)

	@property
	def first_name(self):
		return self.account_holder.split(' ')[0]

	@property
	def last_name(self):
		return ' '.join(self.account_holder.split(' ')[1:])

	# TODO - generalize this
	# currencies accepted by the bank
	@property
	def send(self):
		return ( 'USD', )
	@property
	def recv(self):
		return ( 'USD', )

	@staticmethod
	def get_bank_name(number):
		return Institution.objects.get(routing_number=number).customer_name

PAYMENT_METHODS = (
	('C', 'CryptoAccount'),
	# bank account
	('P', 'PaymentNetworkAccount'),
	('D', 'CreditCard'),
)

# wrapper class around different accounts
class PaymentMethod(models.Model):
	id = models.CharField(max_length=32, primary_key=True, default=crypto.gen_eid)
	foreign_model = models.CharField(max_length=1, choices=PAYMENT_METHODS)
	is_locked = models.BooleanField(default=False)

	# the payment method foreign ID (e.g. BankAccount.id)
	foreign_key = models.CharField(max_length=64)

	def delete(self):
		if self.is_locked:
			raise LockedError()
		return super(PaymentMethod, self).delete()

	# currency.sale(amount): increase the currency for Yellowcoin
	# currency.credit(amount): decrease the currency for Yellowcoin
	def sale(self, user, amount):
		return self.get_object(user).sale(amount)
	def credit(self, user, amount):
		return self.get_object(user).credit(amount)

	# abstract properties - should be implemented by all payment methods
	# send and recv are list of currencies which are supported by the payment method
	@property
	def send(self):
		raise NotImplementedError('.send not implemented by this payment method')

	def lock(self):
		self.is_locked = True
		self.save()

	def unlock(self):
		if not self.is_locked:
			return

		try:
			# if there exists a currently unfinished transaction, we cannot delete the associated payment method
			#	cf. transaction.models.Transaction.TRANSACTION_STATUSES for explanation of each status
			#	cf. http://bit.ly/1d7xzUi
			tx = tuple(self.withdrawal_transactions.all()) + tuple(self.deposit_transactions.all())
			a = next(x for x in tx if (x.status not in ('C', 'U', 'A')))
		except StopIteration:
			self.is_locked = False
			self.save()

	@property
	def recv(self):
		raise NotImplementedError('.recv not implemented by this payment method')

	@property
	def is_confirmed(self):
		raise NotImplementedError('.is_confirmed not implemented by this payment method')

	# get an account by the EID and the user
	@staticmethod
	def static_get_object(id, user):
		return PaymentMethod.objects.get(id=str(id)).get_object(user)

	def get_object(self, user):
		if self.foreign_model == 'C':
			try:
				return CryptoAccount.objects.get(id=self.foreign_key, user=user)
			except CryptoAccount.DoesNotExist:
				raise PaymentMethod.DoesNotExist()
		elif self.foreign_model == 'P':
			for account in user.profile.payment_network.bank_accounts:
				if account.id == self.foreign_key:
					return account
		elif self.foreign_model == 'D':
			for account in user.profile.payment_network.credit_cards:
				if account.id == self.foreign_key:
					return account
		raise PaymentMethod.DoesNotExist()

	# just a convenience method to handle special cases too
	# returns the EID of the method (e.g. BankAccount.eid)
	@staticmethod
	def get_id(foreign_model, foreign_key):
		# if the id is None, then return None
		if foreign_key == None:
			return None
		try:
			obj = PaymentMethod.objects.get(foreign_model=foreign_model, foreign_key=foreign_key)
		except PaymentMethod.DoesNotExist:
			# TODO - this won't work when @transaction.atomic is in play
			#	cf. http://bit.ly/1dm5XhC
			# while True:
			#	try:
					# ensure the ID (a.k.a. EID) is unique
					#	cf. http://bit.ly/KfUfLi
					obj = PaymentMethod(foreign_model=foreign_model, foreign_key=foreign_key)
					obj.save(force_insert=True)
			#		break
			#	except IntegrityError:
			#		pass

		return obj.id

# more payment methods to follow
# class PayPalAccount(models.Model):
#	raise LockedError if self.is_locked
#	def delete():
#		pass
#
#	sale - TAKE currency from user
#	returns ( is_successful, tx_id, {}, ) tuple
#	def sale(self, amount):
#		pass
#
#	credit - GIVE currency to user
#	returns ( is_successful, tx_id, {}, ) tuple
#	def credit(self, amount):
#		pass
#
#	returns a tuple of currency abbreviations
#	@property
#	def send(self):
#		pass
#
#	returns a tuple of currency abbreviations
#	@property
#	def recv(self):
#		pass

class CryptoAccount(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='crypto_accounts')
	address = models.CharField(max_length=34, db_index=True)
	currency = models.CharField(max_length=3, choices=CRYPTOCURRENCIES.items(), default='BTC')
	nickname = models.CharField(max_length=32, blank=True)
	is_default = models.BooleanField(default=False) # see /api/users/views.py:ListCreateCryptoAccounts.post()

	@property
	def eid(self):
		return PaymentMethod.get_id(foreign_model='C', foreign_key=self.id)

	def sale(self, amount):
		# TODO - may want to reuse addresses at some point
		#	this will require the use of listreceivedbyaddress() in conjunction with getreceivedbyaddress()
		#	will also probably need an additional DB to keep track of the current amount received by each address
		address = settings.BTC_CONN.getnewaddress(settings.BTC_ACCT)
		status = { 'amount' : amount, 'address' : address, 'error_data' : {} }
		return ( True, '', status, )

	def credit(self, amount):
		status = { 'amount' : amount, }
		try:
			tx_id = settings.BTC_CONN.sendfrom(settings.BTC_ACCT, self.address, float(amount), comment_to='-- Yellowcoin')
			success = bool(tx_id)
			if not success:
				status['error_message'] = 'Unknown error - please try again or contact us.'
		except InsufficientFunds as aux:
			raise InsufficientFundsException(aux)
		return ( success, tx_id, status, )

	# currencies accepted by the account
	#	for cryptocurrencies, this is just the crypto protocol
	# called on by PaymentMethod.send, PaymentMethod.recv
	@property
	def send(self):
		return ( self.currency, )
	@property
	def recv(self):
		return ( self.currency, )
	@property
	def transactions(self):
		return self.withdrawal_coin_address + self.deposit_coin_address
	# crypto accounts can "always" be debit'd
	@property
	def can_debit(self):
		return True
	@property
	def is_locked(self):
		try:
			return PaymentMethod.objects.get(id=self.eid).is_locked
		# if the record does not exist, offload creating the object until later
		# if the record does not exist, then the method has never been accessed
		#	and thus can be safely assumed to be not locked
		except PaymentMethod.DoesNotExist:
			return False

	def delete(self):
		if self.is_locked:
			raise LockedError()
		PaymentMethod.objects.get(foreign_model='C', foreign_key=self.id).delete()
		return super(CryptoAccount, self).delete()

# Don't use the Token object in DRF because it doesn't permit multiple keys per user
class APIKey(models.Model):
	key = models.CharField(max_length=32, primary_key=True, default=crypto.gen_random_str)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='api_keys')
	comment = models.CharField(max_length=32)
