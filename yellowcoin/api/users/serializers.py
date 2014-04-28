from django.contrib.auth import authenticate
from django.core.paginator import Page # for type detection 
from rest_framework import serializers
from django_routing_numbers import Institution
from yellowcoin.users.models import *
from yellowcoin.api.transactions.serializers import OrderTemplateSerializer
from yellowcoin.enums import CRYPTOCURRENCIES
from hashlib import sha256
import xmltodict
import struct
import ctypes
import requests
from balanced_yellowcoin import balanced as payment_network

class SettingSerializer(serializers.ModelSerializer):
	class Meta:
		model = User
		fields = ('two_factor_authentication', 'api_access', 'one_click', 'one_click_order_template')
	two_factor_authentication = serializers.BooleanField(source='use_2fa', required=False)
	api_access = serializers.BooleanField(source='use_api', required=False)
	one_click = serializers.BooleanField(source='use_one_click', required=False)
	one_click_order_template = OrderTemplateSerializer(required=False)

	def validate_two_factor_authentication(self, attrs, source):
		if 'two_factor_authentication' in self.init_data and not self.context['request'].user.profile.valid_phone:
			raise serializers.ValidationError('Phone number not verified')
		return attrs

class NotificationSerializer(serializers.Serializer):
	login = serializers.BooleanField(required=False, default=False)
	start_transaction = serializers.BooleanField(required=False, default=False)
	end_transaction = serializers.BooleanField(required=False, default=False)
	profile = serializers.BooleanField(required=False, default=False)
	bank_account = serializers.BooleanField(required=False, default=False)
	coin_address = serializers.BooleanField(required=False, default=False)

	def to_native(self, obj):
		if obj is not None:
			for field_name, field in self.fields.items():
				if field_name not in obj:
					obj[field_name] = field.default
		return super(NotificationSerializer, self).to_native(obj)

class ValidateBankAccountSerializer(serializers.Serializer):
	micropayment_1 = serializers.DecimalField(max_digits=3, decimal_places=2)
	micropayment_2 = serializers.DecimalField(max_digits=3, decimal_places=2)

class LoginRecordSerializer(serializers.Serializer):
	class Meta:
		model = LoginRecord
	timestamp = serializers.DateTimeField()
	ip = serializers.Field(source='ip')
	location = serializers.CharField()

class ProfileSerializer(serializers.Serializer):
	class Meta:
		model = Profile
		write_only_fields = ('current_password','password',)
		read_only_fields = ('valid_profile',)
	email = serializers.CharField(source='user.unconfirmed_email', required=False)
	first_name = serializers.CharField(source='payment_network.billing_address.first_name', required=False)
	last_name = serializers.CharField(source='payment_network.billing_address.last_name', required=False)
	address1 = serializers.CharField(source='payment_network.billing_address.street1', required=False)
	address2 = serializers.CharField(source='payment_network.billing_address.street2', required=False)
	city = serializers.CharField(source='payment_network.billing_address.city', required=False)
	state = serializers.CharField(source='payment_network.billing_address.state', required=False)
	zip = serializers.CharField(source='payment_network.billing_address.postal', required=False)
	phone = serializers.CharField(source='payment_network.billing_address.phone', required=False)
	ssn = serializers.CharField(source='ssn', required=False)

	gender = serializers.ChoiceField(source='gender', required=False, choices=( ('male', 'M'), ('female', 'F'), ))
	passport = serializers.CharField(source='passport', required=False)
	dob = serializers.DateField(source='dob', required=False)

	password = serializers.CharField(required=False)
	current_password = serializers.CharField()
	
	is_valid = serializers.SerializerMethodField('get_validity_object')

	def validate_ssn(self, attrs, source):
		return self._restrict_valid_profile(attrs, source)
	
	def validate_passport(self, attrs, source):
		return self._restrict_valid_profile(attrs, source)

	def validate_dob(self, attrs, source):
		return self._restrict_valid_profile(attrs, source)

	def _restrict_valid_profile(self, attrs, source):
		if self.object and self.object.user.profile.valid_profile:
			raise serializers.ValidationError('This profile has already been validated.')
		return attrs

	def to_native(self, obj):
		ret = self._dict_class()
		ret.fields = self._dict_class()
		for field_name, field in self.fields.items():
			if field.read_only and obj is None:
				continue
			elif field_name in getattr(self.Meta, 'write_only_fields', ()):
				key = self.get_field_key(field_name)
				ret.fields[key] = self.augment_field(field, field_name, key, '')
			else:
				field.initialize(parent=self, field_name=field_name)
				key = self.get_field_key(field_name)
				value = field.field_to_native(obj, field_name)
				method = getattr(self, 'transform_%s' % field_name, None)
				if callable(method):
					value = method(obj, value)
				ret[key] = value
				ret.fields[key] = self.augment_field(field, field_name, key, value)
		return ret

	def validate_current_password(self, attrs, source):
		if self.object is None:
			return attrs
		u = authenticate(username=self.object.user.email, password=attrs[source])
		if u is not None:
			return attrs
		else:
			raise serializers.ValidationError('The password supplied is invalid.')
		
	def get_validity_object(self, obj):
		if not hasattr(obj, 'user'):
			return False
		return {
			'email' : obj.valid_email,
			'bank_account' : obj.valid_bank_account,
			'profile' : obj.valid_profile,
			'phone' : obj.valid_phone
		}

class CryptoAccountSerializer(serializers.ModelSerializer):
	class Meta:
		model = CryptoAccount
		exclude = ( 'user', )
		write_only_fields = ('currency',)
	id = serializers.CharField(source='eid', read_only=True)
	is_locked = serializers.BooleanField(read_only=True)
	is_default = serializers.BooleanField(required=False)
	display = serializers.SerializerMethodField('get_display_name')
	receives = serializers.Field(source='recv')
	sends = serializers.Field(source='send')

	def get_display_name(self, obj):
		if obj.nickname:
			return "%s - %s" % (obj.nickname, obj.address)
		else:
			return obj.address

	# address validation
	#	cf http://bit.ly/1bIpdku
	def validate_address(self, attrs, source):
		if attrs['currency'] == 'BTC':
			try:
				addr_bytes = self.decode_base58(attrs[source], 25)
			except:
				raise serializers.ValidationError('Invalid address')
			if not addr_bytes[-4:] == sha256(sha256(addr_bytes[:-4]).digest()).digest()[:4]:
				raise serializers.ValidationError('Invalid address')
		else:
			raise serializers.ValidationError('Invalid currency')

		if CryptoAccount.objects.filter(user=self.context['request'].user, address=attrs[source]).exists():
			raise serializers.ValidationError('Duplicate address found')
		
		return attrs

	def decode_base58(self, addr, length):
		digits58 = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz'
		n = 0
		for char in addr:
			n = n * 58 + digits58.index(char)
		data = ctypes.create_string_buffer(length)
		for i in range(length):
			struct.pack_into(">c", data, len(data) - i - 1, chr(n & ((1 << 8) - 1)))
			n = n >> 8
		return data

class BankAccountSerializer(serializers.Serializer):
	id = serializers.CharField(source='eid', read_only=True)
	is_locked = serializers.BooleanField(source='is_locked', read_only=True)
	# read-only by default
	bank_name = serializers.Field(source='routing_number')
	is_confirmed = serializers.BooleanField(source='can_debit', read_only=True)
	is_default = serializers.BooleanField()
	first_name = serializers.CharField()
	last_name = serializers.CharField()
	routing_number = serializers.CharField()
	account_number = serializers.CharField()
	type = serializers.CharField()

	display = serializers.SerializerMethodField('get_display_name')
	receives = serializers.Field(source='recv')
	sends = serializers.Field(source='send')
	
	def get_display_name(self, obj):
		# this is true during POST requests
		if isinstance(obj, dict):
			return "%s - %s" % ( self.transform_bank_name(obj, obj['routing_number']), self.transform_account_number(obj, obj['account_number']), )
		# this is true during object instantiation
		else:
			return "%s - %s" % ( obj.bank_name, obj.account_number, )

	@property
	def mask(self):
		return self._mask

	@mask.setter
	def mask(self, value):
		self._mask = value
		if self._data is not None:
			if self.many or hasattr(self._data, '__iter__') and not isinstance(self._data, (Page, dict)):
				for obj in self._data:
					obj['account_number'] = self.transform_account_number(obj, obj['account_number'])
			else:
				self._data['account_number'] = self.transform_account_number(self._data, self._data['account_number'])

	def __init__(self, *args, **kwargs):
		if 'mask' in kwargs:
			self._mask = kwargs['mask']
			del kwargs['mask']
		else:
			self._mask = True
		super(BankAccountSerializer, self).__init__(*args, **kwargs)

	def transform_type(self, obj, value):
		if value == payment_network.BankAccount.CHECKING:
			return 'C'
		if value == payment_network.BankAccount.SAVINGS:
			return 'S'
		return value

	def transform_bank_name(self, obj, value):
		try:
			return BankAccount.get_bank_name(value)
		except:
			return ""

	def transform_account_number(self, obj, value):
		if not self._mask:
			return value
		value = str(value)
		if len(value) < 4:
			return ('X' * (9 - len(value))) + value
		else:
			return ('X' * 5) + value[-4:]
		
	def validate_type(self, attrs, source):
		attrs[source] = attrs[source].upper()[0]
		return attrs

	def validate_routing_number(self, attrs, source):
		try:
			Institution.objects.get(routing_number=attrs[source])
			return attrs
		except:
			raise serializers.ValidationError('Invalid routing number')

	def validate_account_number(self, attrs, source):
		try:
			int(attrs[source])
			return attrs
		except ValueError:
			raise serializers.ValidationError('Invalid account number')

class AccountSerializer(serializers.Serializer):
	bank = serializers.SerializerMethodField('bank_account_serializer')
	
	def __init__(self, *args, **kwargs):
		# dynamically add the cryptocurrency types
		for currency, name in CRYPTOCURRENCIES.items():
			self.base_fields[currency] = serializers.SerializerMethodField('coin_address_serializer_%s' % currency)
		super(AccountSerializer, self).__init__(*args, **kwargs)

	def __getattr__(self, name):
		if name.startswith('coin_address_serializer_'):
			return lambda obj:self.coin_account_serializer(name[24:], obj)
		return super(AccountSerializer, self).__getattr__(name)

	def coin_account_serializer(self, currency, obj):
		return CryptoAccountSerializer(obj.crypto_accounts.filter(currency=currency), many=True).data

	def bank_account_serializer(self, obj):
		return BankAccountSerializer(obj.bank_accounts, many=True).data

class PaymentMethodSerializer(serializers.ModelSerializer):
	class Meta:
		model = PaymentMethod
