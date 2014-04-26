from rest_framework import serializers
from yellowcoin.transactions.models import *
from yellowcoin.users.models import *
import requests
import datetime
from decimal import Decimal
from yellowcoin.enums import CURRENCIES, CRYPTOCURRENCIES
from django.conf import settings

class BidCryptoAddressField(serializers.RelatedField):
	read_only = False
	def to_native(self, obj):
		return obj.address

	def from_native(self, obj):
		from yellowcoin.api.users.serializers import CryptoAccountSerializer, BankAccountSerializer
		return CryptoAccountSerializer(obj.data).object

class AskCryptoAddressField(serializers.RelatedField):
	read_only = False
	def to_native(self, obj):
		return obj.address

	def from_native(self, obj):
		from yellowcoin.api.users.serializers import CryptoAccountSerializer, BankAccountSerializer
		return CryptoAccountSerializer(obj.data).object

class OrderSerializer(serializers.ModelSerializer):
	class Meta:
		model = Order
		exclude = ( 'ask_transaction', 'bid_transaction' )
		read_only_fields = ('id', 'bid_fee', 'ask_fee', 'timestamp', 'exchange_rate', 'bid_currency', 'ask_currency')

	# the currency is given in the URL - /bid/ask/
	bid_subtotal = serializers.DecimalField(max_digits=20, decimal_places=8, default=0)
	ask_subtotal = serializers.DecimalField(max_digits=20, decimal_places=8, default=0)
	withdrawal_account = serializers.PrimaryKeyRelatedField(many=False, queryset=PaymentMethod._default_manager, write_only=True)
	deposit_account = serializers.PrimaryKeyRelatedField(many=False, queryset=PaymentMethod._default_manager, write_only=True)
	comment = serializers.CharField(max_length=255, required=False, default='', write_only=True)

	def validate_subtotal(self, attrs, source, currency):
		if attrs[source] <= 0:
			raise serializers.ValidationError('Subtotal must be positive.')
                try:
			limit = TransactionLimit.objects.get(
						user=self.context['request'].user,
						currency=currency
					)
		except TransactionLimit.DoesNotExist:
			limit = self.context['request'].user.get_limit(currency)

		if Decimal(attrs[source]) > limit:
			raise serializers.ValidationError('This amount exceeds your total limit for this currency')

		if (currency == u'USD') and (attrs[source] < settings.MIN_USD_TX):
			raise serializers.ValidationError('Minimum transaction amount of $%.2f USD not met' % settings.MIN_USD_TX)

		return attrs

	def validate_bid_subtotal(self, attrs, source):
		return self.validate_subtotal(attrs, source, self.init_data.get('bid_currency', ''))

	def validate_ask_subtotal(self, attrs, source):
		return self.validate_subtotal(attrs, source, self.init_data.get('ask_currency', ''))

	def validate_account(self, attrs, source, currency_key, direction, direction_message):
		try:
			method = attrs[source].get_object(self.context['request'].user)
		except PaymentMethod.DoesNotExist:
			raise serializers.ValidationError("Invalid pk '%s' - object does not exist." % attrs[source].id)
		if currency_key in self.init_data:
			currency = self.init_data[currency_key]
			if currency not in getattr(method, direction):
				raise serializers.ValidationError("This account cannot %s %s" % (direction_message, currency))
			if not method.can_debit:
				raise serializers.ValidationError('This account has not been confirmed.')
		return attrs

	def validate_deposit_account(self, attrs, source):
		return self.validate_account(attrs, source, 'ask_currency', 'recv', 'receive')

	def validate_withdrawal_account(self, attrs, source):
		return self.validate_account(attrs, source, 'bid_currency', 'send', 'send')

	def validate(self, attrs):
		if attrs.get('withdrawal_payment_method', 0) == attrs.get('deposit_payment_method', 1):
			raise serializers.ValidationError('Accounts must be different.')
		return attrs

	def restore_object(self, attrs, instance=None):
		if 'withdrawal_account' in attrs:
			data = dict([(k, v) for (k, v) in attrs.items() if k not in ('comment', 'withdrawal_account', 'deposit_account')])
		else:
			data = attrs
		return super(OrderSerializer, self).restore_object(data, instance)

	def save_object(self, obj, **kwargs):
		data = self.init_data
		for (k, v) in self.data.items():
			# this is a little sketchy, but it works for us
			#	data contains parsed values, which we need, but doesn't contain write_only fields
			if v:
				data[k] = v
		# cheat a little bit lol. have it generate to_native() again. I have no idea where obj is from...
		# TODO: is_api
		self.object = Order.objects.create_order(self.context['request'].GET.get('key') is not None, self.context['request'].META.get('REMOTE_ADDR'), self.context['request'].user, data['bid_currency'], data['ask_currency'], data)
		self._data = None
		return self.object

class OrderTemplateSerializer(OrderSerializer):
	class Meta:
		model = OrderTemplate
		read_only_fields = ('id',)
		write_only_fields = tuple()
		exclude = ('user','bid_subtotal', 'ask_subtotal', 'comment','withdrawal_payment_method','deposit_payment_method')
	
	subtotal = serializers.DecimalField(max_digits=20, decimal_places=8, default=0)
	withdrawal_account = serializers.PrimaryKeyRelatedField(many=False, queryset=PaymentMethod._default_manager, source='withdrawal_payment_method')
	deposit_account = serializers.PrimaryKeyRelatedField(many=False, queryset=PaymentMethod._default_manager, source='deposit_payment_method')

	def validate_subtotal(self, attrs, source):
		if 'type' in self.init_data:
			if self.init_data['type'].upper()[0] == 'A':
				return super(OrderTemplateSerializer, self).validate_subtotal(
					attrs, source, self.init_data['ask_currency'])
			else:
				return super(OrderTemplateSerializer, self).validate_subtotal(
					attrs, source, self.init_data['bid_currency'])
		elif attrs[source] < 0:
			raise serializers.ValidationError('Subtotal must be positive.')
		return attrs

	def save_object(self, obj, **kwargs):
		return super(OrderSerializer, self).save_object(obj, **kwargs)

class OrderTemplateField(serializers.PrimaryKeyRelatedField):
	def to_native(self, value):
		return OrderTemplateSerializer(OrderTemplate.objects.get(id=value)).data

class RecurringOrderSerializer(serializers.ModelSerializer):
	class Meta:
		model = RecurringOrder
		read_only_fields = ('id','last_run')
		exclude = ('user',)
	template = OrderTemplateField()
	next_run = serializers.SerializerMethodField('get_next_run')

	def get_next_run(self, obj):
		return obj.last_run + datetime.timedelta(seconds=obj.interval)

	def validate_template(self, attrs, source):
		if attrs[source].user != self.context['request'].user:
			raise serializers.ValidationError("Invalid pk '%s' - object does not exist." % attrs[source].id)
		return attrs

class TransactionSerializer(serializers.ModelSerializer):
	class Meta:
		model = Transaction
		exclude = ( 'id', 'fingerprint', 'error_data', 'is_api', 'user', 'withdrawal_payment_method', 'deposit_payment_method')
		read_only = ( 'is_reoccuring', )
	order = OrderSerializer(source='order', read_only=True, many=False)
	deposit_address = serializers.CharField(source='deposit_address', read_only=True)
	error_message = serializers.CharField(source='error_message', read_only=True)
	# Conveniently, these are named differently on the frontend. TODO: figure out why field overwriting no worky. Django REST Framework bug?
	withdrawal_account = serializers.SerializerMethodField('get_withdrawal_payment_method')
	deposit_account = serializers.SerializerMethodField('get_deposit_payment_method')
	status = serializers.CharField(source='get_status_display')
	
	def get_withdrawal_payment_method(self, obj):
		if obj.withdrawal_payment_method:
			return self.__serialize_payment_method(obj.withdrawal_payment_method, obj.user)
		return {}

	def get_deposit_payment_method(self, obj):
		if obj.deposit_payment_method:
			return self.__serialize_payment_method(obj.deposit_payment_method, obj.user)
		return {}

	def __serialize_payment_method(self, payment_method, user):
		if not hasattr(self, '_payment_method_cache'):
			self._payment_method_cache = {}
		if payment_method.id not in self._payment_method_cache:
			if payment_method.foreign_model == 'C':
				from yellowcoin.api.users.serializers import CryptoAccountSerializer, BankAccountSerializer
				self._payment_method_cache[payment_method.id] = CryptoAccountSerializer(payment_method.get_object(user), many=False).data
			elif payment_method.foreign_model == 'P':
				from yellowcoin.api.users.serializers import CryptoAccountSerializer, BankAccountSerializer
				self._payment_method_cache[payment_method.id] = BankAccountSerializer(payment_method.get_object(user), many=False).data
		try:
			return self._payment_method_cache[payment_method.id]
		except KeyError:
			raise Exception('Payment method \'%s\' not found' % payment_method.foreign_model)

class TransactionLimitSerializer(serializers.ModelSerializer):
	class Meta:
		model = TransactionLimit
		fields = ( 'cur_amount', 'max_amount', )
