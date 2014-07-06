from django.http import Http404
from django.db import transaction
from django.shortcuts import *
from django.views.generic import *
from rest_framework.exceptions import *
from rest_framework import generics, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from yellowcoin.users.models import *
import yellowcoin.users.signals
from yellowcoin.api.exceptions import *
from yellowcoin.api.users.serializers import *
from yellowcoin import crypto
from yellowcoin.users import signals
from random import random
from balanced_yellowcoin import balanced as payment_network
from django_otp_twilio_yellowcoin.models import TwilioSMSDevice
import requests
import time
from yellowcoin.enums import *

# debug
from pprint import pformat

class ListAccounts(generics.RetrieveAPIView):
	"""
	Retrieve or create payment accounts

	See the individual endpoints at <code>/api/users/accounts/(bank|credit)/</code> and <code>/api/users/accounts/&lt;currency&gt;/</code> for details on each account type.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = AccountSerializer
	def get_object(self):
		return self.request.user	
	def get_queryset(self):
		return self.request.user

class RetrieveUpdateSettings(generics.RetrieveUpdateAPIView):
	"""
	Retrieve or update account settings.
	
	GET two_factor_authentication <- Whether two-factor authentication is enabled e.g. false
	PUT two_factor_authentication -> Enable or disable two-factor authentication. Requires a validated phone number. e.g. true
	GET one_click <- Whether one-click ordering is enabled e.g. false
	PUT one_click -> Enable or disable one-click ordering. e.g. true
	GET one_click_order_template <- The order template bound to one-click.
	PUT one_click_order_template -> The id of the order template to rebind to.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = SettingSerializer

	def get_object(self):
		return self.request.user	

	def get_queryset(self):
		return self.request.user

class RetrieveUpdateNotifications(generics.RetrieveUpdateAPIView):
	"""
	Set user notification settings.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = NotificationSerializer

	defaults = {
		'email':{
			'login':False,
			'login_failed':False, 
			'start_transaction':False,
			'end_transaction':False,
			'update_profile':False,
			'create_bank_account':False,
			'create_coin_address':False,
			'referral_completed':False
		},
		'sms':{
			'login':False, 
			'login_failed':False, 
			'start_transaction':False,
			'end_transaction':False,
			'update_profile':False,
			'create_bank_account':False,
			'create_coin_address':False,
			'referral_completed':False
		}
	}
	def get(self, request, medium=None, format=None):
		if medium not in (None, 'sms', 'email'):
			raise Http404()
		queryset = self.get_queryset()
		return Response(queryset if medium is None else queryset[medium], status=200)

	def put(self, request, medium=None, format=None):
		if medium not in (None, 'sms', 'email'):
			raise Http404()
		queryset = self.get_queryset()

		if medium:
			from_form = False
			for key, value in request.DATA.items():
				if value == 'on':
					from_form = True
			
			if from_form:
				for key in self.defaults[medium]:
					request.DATA[key] = (request.DATA[key] == 'on' if key in request.DATA else False)

		def inject(original, data):
			for key, value in data.items():
				if key in original:
					original[key] = value
			return original
		if medium == None:
			for key in request.DATA:
				if key in queryset:
					queryset[key] = inject(queryset[key], request.DATA[key])
		else:
			queryset[medium] = inject(queryset[medium], request.DATA)

		self.request.user.store('notifications', queryset)
		self.request.user.save()

		return Response(queryset if medium is None else queryset[medium], status=200)

	def get_queryset(self):
		queryset = self.request.user.retrieve('notifications', self.defaults)
		for m in self.defaults.keys():
			# merge in changes
			queryset[m] = dict(self.defaults[m].items() + (queryset[m].items() if m in queryset else {}.items()))
		return queryset

class RetrieveUpdateProfile(generics.RetrieveUpdateAPIView):
	"""
	Retrieve or update profile settings.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = ProfileSerializer
	def get_object(self):
		return self.request.user.profile

	def put(self, request, format=None):
		serializer = self.get_serializer(instance=request.user.profile, data=request.DATA)
		profile_valid = request.user.profile.valid_profile
		retries_remaining = request.user.profile.retries_remaining

		if serializer.is_valid():
			serializer.save()

			# TODO - Minke fix bug, this will be called when phone is not updated
			# desired behavior is to call only when phone updated, see email code.
			# add phone
			if request.user.profile.payment_network.billing_address.phone:
				# delete all old records
				TwilioSMSDevice.objects.filter(user=self.request.user).delete()
				# insert new record
				TwilioSMSDevice.objects.create(number=request.user.profile.payment_network.billing_address.phone, user=self.request.user).save()

			signals.update_profile.send(sender=request, user=request.user)
			if 'password' in request.DATA:
				request.user.set_password(request.DATA['password'])
				request.user.save()
				signals.update_password.send(sender=request, user=request.user)
			if 'email' in request.DATA:
				# everything else is handled by the model
				signals.create_account.send(sender=request, user=request.user)
			if((not request.user.profile.valid_profile) and (request.user.profile.retries_remaining <= 0)):
				raise GenericException({ 'non_field_errors' : [ 'Profile validation attempts exceeded', ] }, status=403)
			if((not request.user.profile.retries_remaining == retries_remaining) and not request.user.profile.valid_profile):
				raise GenericException({ 'non_field_errors' : [ 'Profile validation error', ] }, status=400)
			return Response(serializer.data, status=200)

		raise GenericException(serializer.errors, status=400)

	def get_queryset(self):
		return self.request.user.profile

class ValidateBankAccount(generics.UpdateAPIView):
	"""
	Verify a bank account
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = ValidateBankAccountSerializer

	def put(self, request, id):
		try:
			id = PaymentMethod.static_get_object(id, self.request.user).id
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		serializer = self.get_serializer(data=request.DATA)

		# micropayments values in CENT form, not DOLLAR form
		serializer.data['micropayment_1'] = request.DATA[u'micropayment_1']
		serializer.data['micropayment_2'] = request.DATA[u'micropayment_2']
		client = self.request.user.profile.payment_network

		# get bank account
		try:
			# cf. http://bit.ly/1eoQCvx
			account = next(x for x in client.bank_accounts if x.id == id)
		except StopIteration:
			raise GenericException(status=404)

		if account.can_debit:
			return Response({}, status=200)

		try:
			result = account.validate(serializer.data['micropayment_1'], serializer.data['micropayment_2'])
		# as per http://bit.ly/P9ZkX7, max retry limit of three attempts
		#	an exception is thrown if max retry limit is exceeded
		except Exception as e:
			raise GenericException({ 'non_field_errors' : [ 'You have tried to validate this bank account too many times. The bank account has been locked. Please contact us for assistance.' ] }, status=403)

		if result:
			account.save()
			return Response({}, status=200)

		# incorrect values
		raise GenericException({ 'non_field_errors' : [ 'The input values were incorrect.' ] }, status=400)
	
# BITCOIN ADDRESS VIEWS

# view, add, edit crypto accounts
class ListCreateCryptoAccounts(generics.ListCreateAPIView):
	"""
	Retrieve or create cryptocurrency accounts.

	<span class="label label-success">GET</span> <span class="label label-info">POST</span> <code>/api/accounts/&lt;currency&gt;/</code> - List or create new cryptocurrency accounts.

	<span class="label label-success">GET</span> <span class="label label-warning">PUT</span> <span class="label label-danger">DELETE</span> <code>/api/accounts/&lt;currency&gt;/&lt;id&gt;/</code> - Get a specific cryptocurrency account.
	"""
	permission_classes = ( IsAuthenticated, )
	# TODO - rename to CoinAccountSerializer
	serializer_class = CryptoAccountSerializer
	# paginate_by = 100

	@transaction.atomic
	def post(self, request, currency):
		data = request.DATA.copy()
		data['currency'] = currency.upper()
		serializer = self.get_serializer(data=data)
		if serializer.is_valid():
			# deserialize to gain access to manually-set user field
			#	cf http://bit.ly/1fAo6bM
			serializer.object.user = self.request.user
			if serializer.object.is_default:
				self.get_queryset().update(is_default=False)
			else:
				serializer.object.is_default = not self.get_queryset().filter(is_default=True).exists()
			serializer.save()
			# set serializer data
			serializer.data['id'] = serializer.object.eid
			signals.create_crypto_account.send(sender=request, user=request.user, account=serializer.object)
			return Response(serializer.data, status=201)
		raise GenericException(status=400, detail=serializer.errors)

	def get_queryset(self):
		return CryptoAccount.objects.filter(user=self.request.user, currency=self.kwargs['currency'].upper())

# get and delete single instance
class RetrieveUpdateDestroyCryptoAccount(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = ( IsAuthenticated, )
	serializer_class = CryptoAccountSerializer

	def get_serializer_class(self):
		if self.request.method == 'PUT':
			return serializers.Serializer
		return super(RetrieveUpdateDestroyCryptoAccount, self).get_serializer_class()

	# set default to true
	def put(self, request, currency, id):
		try:
			id = PaymentMethod.static_get_object(id, self.request.user).id
			protocol = currency.upper()
			# set all other accounts to false
			self.request.user.crypto_accounts.filter(currency=protocol).exclude(id=id).update(is_default=False)

			crypto_account = self.request.user.crypto_accounts.get(id=id)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)

		crypto_account.is_default = True
		crypto_account.save()

		return Response([], status=200)

	def get(self, request, currency, id):
		try:
			crypto_account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		return Response(self.get_serializer(instance=crypto_account).data, status=200)

	def delete(self, request, currency, id):
		try:
			crypto_account = PaymentMethod.static_get_object(id, self.request.user)
			try:
				crypto_account.delete()
			except LockedError:
				raise GenericException({ 'non_field_errors' : [ 'The account is locked at this time due to a pending transaction.' ] }, status=409)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		return Response([], status=204)

class RetrieveUpdateDestroyCreditCard(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = ( IsAuthenticated, )
	serializer_class = CreditCardSerializer

	def get_serializer_class(self):
		if self.request.method == 'PUT':
			return(serializers.Serializer)
		return(super(RetrieveUpdateDestroyCreditCard, self).get_serializer_class())

	def put(self, request, id, *args, **kwargs):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise(GenericException(status=404))
		if account.can_debit:
			account.is_default = True
			account.save()
			return(Response([], status=200))
		errors = { 'is_default' : 'Cannot set default on an account which is not verified' }
		raise(GenericException(status=400, detail=errors))

	def get(self, request, id, *args, **kwargs):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		serializer = self.get_serializer(CreditCard(account), many=False)
		return Response(serializer.data, status=200)

	def delete(self, request, id):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		try:
			account.delete()
		except LockedError:
			raise GenericException({ 'non_field_errors' : [ 'The account is locked at this time due to a pending transaction.' ] }, status=409)
		return Response([], status=204)

class ListCreateCreditCards(generics.ListCreateAPIView):
	"""
	Retrieve or create credit / debit accounts.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = CreditCardSerializer
	# paginate_by = 100

	@transaction.atomic
	def post(self, request, format=None):
		serializer = CreditCardSerializer(data=request.DATA, mask=False)
		if serializer.is_valid():
			# create client payment_network_id if none exists yet
			client = self.request.user.profile.payment_network

			# add account
			serializer.data['is_confirmed'] = False
			serializer.data['is_default'] = False
			credit_debit_account = CreditCard(payment_network.CreditCard.create(
				account_holder='%s %s' % (serializer.data['first_name'], serializer.data['last_name']),
				# custom data field
				iin=serializer.data['account_number'][0:6],
				# this field is hidden from us from now on
				account_number=serializer.data['account_number'],
				expiry=serializer.data['expiry'],
				is_default=serializer.data['is_default'],
				is_confirmed=serializer.data['is_confirmed'],
				cvv2=serializer.data['cvv2'],
			))
			if not self.request.user.profile.first_name:
				self.request.user.profile.first_name = serializer.data['first_name']
			if not self.request.user.profile.last_name:
				self.request.user.profile.last_name = serializer.data['last_name']
			for account in self.request.user.profile.payment_network.credit_cards:
				if account.account_number == serializer.data['account_number']:
					serializer.errors['account_number'] = ['This credit / debit account already exists']
					raise GenericException(serializer.errors, status=400)
			client.add_payment_method(credit_debit_account)
			client.save()

			# validate credit card
			credit_debit_account.is_confirmed = ResponseParser.parse(credit_debit_account.authorize(0))
			credit_debit_account.save()

			signals.create_bank_account.send(sender=request, user=request.user, account=credit_debit_account)
			serializer.data['id'] = credit_debit_account.eid
			serializer.mask = True
			return Response(serializer.data, status=201)

		raise ParseError(serializer.errors)

	def get_queryset(self):
		queryset = self.request.user.profile.payment_network.credit_cards
		return queryset

# get, update, delete single bank account
class RetrieveUpdateDestroyBankAccount(generics.RetrieveUpdateDestroyAPIView):
	permission_classes = ( IsAuthenticated, )
	serializer_class = BankAccountSerializer

	def get_serializer_class(self):
		if self.request.method == 'PUT':
			return serializers.Serializer
		return super(RetrieveUpdateDestroyBankAccount, self).get_serializer_class()

	# set default to true
	def put(self, request, id, *args, **kwargs):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		if account.can_debit:
			account.is_default = True
			account.save()
			return Response([], status=200)
		errors = { 'is_default' : 'Cannot set default on an account which is not verified' }
		raise GenericException(status=400, detail=errors)

	def get(self, request, id, *args, **kwargs):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		serializer = self.get_serializer(BankAccount(account), many=False)
		return Response(serializer.data, status=200)

	def delete(self, request, id):
		try:
			account = PaymentMethod.static_get_object(id, self.request.user)
		except PaymentMethod.DoesNotExist:
			raise GenericException(status=404)
		try:
			account.delete()
		except LockedError:
			raise GenericException({ 'non_field_errors' : [ 'The account is locked at this time due to a pending transaction.' ] }, status=409)
		return Response([], status=204)

class ListCreateBankAccounts(generics.ListCreateAPIView):
	"""
	Retrieve or create bank accounts.
	"""
	permission_classes = ( IsAuthenticated, )
	serializer_class = BankAccountSerializer
	# paginate_by = 100

	@transaction.atomic
	def post(self, request, format=None):
		serializer = BankAccountSerializer(data=request.DATA, mask=False)
		if serializer.is_valid():
			# create client payment_network_id if none exists yet
			client = self.request.user.profile.payment_network

			# add bank account
			serializer.data['is_confirmed'] = False
			serializer.data['is_default'] = False
			bank_account = BankAccount(payment_network.BankAccount.create(
				account_holder='%s %s' % (serializer.data['first_name'], serializer.data['last_name']),
				routing_number=serializer.data['routing_number'],
				account_number=serializer.data['account_number'],
				account_type=serializer.data['type'].lower(),
				is_default=serializer.data['is_default'],
				is_confirmed=serializer.data['is_confirmed'],
			))
			if not self.request.user.profile.first_name:
				self.request.user.profile.first_name = serializer.data['first_name']
			if not self.request.user.profile.last_name:
				self.request.user.profile.last_name = serializer.data['last_name']
			for account in self.request.user.profile.payment_network.bank_accounts:
				if ( account.routing_number, account.account_number[-4:], account.account_type ) == ( serializer.data['routing_number'], serializer.data['account_number'][-4:], serializer.data['type'].lower() ):
					serializer.errors['account_number'] = ['This bank account already exists']
					raise GenericException(serializer.errors, status=400)
			client.add_payment_method(bank_account)
			client.save()
			signals.create_bank_account.send(sender=request, user=request.user, account=bank_account)
			serializer.data['id'] = bank_account.eid
			serializer.mask = True

			return Response(serializer.data, status=201)

		raise ParseError(serializer.errors)

	def get_queryset(self):
		queryset = self.request.user.profile.payment_network.bank_accounts
		return queryset

# parsing PaymentNetwork responses
#	in particular, checking the status of ATMVerify to screen untrustworthy accounts
#	cf http://bit.ly/1c1G4mY
class ResponseParser():
	@staticmethod
	def parse((result, tx_id, response)):
		if response['respstat'] != 'A':
			raise VerificationException()
		return True
