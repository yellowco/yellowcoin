from django.db import models, IntegrityError
from django.conf import settings
from django.utils import timezone
from picklefield.fields import PickledObjectField
from yellowcoin import crypto
from yellowcoin.api.exceptions import BadProtocolException
from yellowcoin.users.models import User, PaymentMethod, CryptoAccount
from yellowcoin.enums import CRYPTOCURRENCIES, CURRENCIES
from yellowcoin.currencypool.models import POOLS
from decimal import Decimal

ROLES = {
	'A' : ( 'A', 'Ask', ),
	'B' : ( 'B', 'Bid', ),
}

TRANSACTION_STATUSES = (
	( 'U', 'Uninitialized' ),	# the order has not yet been processed by the task queue
	( 'I', 'Initialized', ),	# the transaction has met certain minimal criteria and environmental sanity checks
	( 'P', 'Pending', ),		# awaiting user action in depositing cryptocurrency
	( 'Q', 'Queried', ),		# server-side status -- awaiting withdrawal confirmation
	( 'R', 'Received', ),		# the task queue has received the payment from the withdrawal account
	( 'C', 'Completed', ),		# the task queue has successfully filled the deposit account (as reported by .sale or .credit)
	( 'D', 'Deleted' ),		# requested a cancellation
					#	the associated payment_method can be deleted
	( 'A', 'Abandoned' ),		# an uninitalized method can never be initialized if the withdrawal or deposit account has been deleted
)

class TransactionManager(models.Manager):
	def filter_active(self, **kwargs):
		return Transaction.objects.filter(**kwargs).exclude(status='A').exclude(status='D').exclude(order=None)

# data about the transaction which should not be visible to the other party
class Transaction(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transactions')

	is_reoccuring = models.BooleanField(default=False)

	comment = models.CharField(max_length=255, blank=True)
	is_api = models.BooleanField(default=False)

	# auxiliary transaction data - should not be unpickled unless needed
	#	address - the coin address
	# TODO - extend user.fingerprint as per DRY
	fingerprint = PickledObjectField()
	ip = models.GenericIPAddressField()

	# TODO - use limit_choices_to
	#	cf. http://bit.ly/1e2xZgj
	withdrawal_payment_method = models.ForeignKey('users.PaymentMethod', related_name='withdrawal_transactions', on_delete=models.SET_NULL, null=True)
	deposit_payment_method = models.ForeignKey('users.PaymentMethod', related_name='deposit_transactions', on_delete=models.SET_NULL, null=True)

	# ( payment_method_type, tx_id, ) : unique transaction ID to keep track of order status
	#	currenly, either a blockchain tx ID or PaymentNetwork tx ID
	# PaymentNetwork contains all important banking information
	# the blockchain id - SHA-256 hash format
	#	64 chars, as per blockchain.info
	withdrawal_tx_id = models.CharField(max_length=64, blank=True, default='')
	deposit_tx_id = models.CharField(max_length=64, blank=True, default='')

	# the original rate of the pool at 'U' => 'I' state change
	#	set in transactions/tasks.py
	initial_exchange_rate = models.DecimalField(max_digits=20, decimal_places=10, null=True)

	objects = TransactionManager()

	# aliases of _payment_method
	# specifically does NOT return the physical account, as we wish to use PaymentMethod
	#	as an interface
	@property
	def withdrawal_account(self):
		return self.withdrawal_payment_method
		# return PaymentMethod.get_object(self.withdrawal_payment_method.id, self.user)

	@property
	def deposit_account(self):
		return self.deposit_payment_method
		# return PaymentMethod.get_object(self.deposit_payment_method.id, self.user)

	# current transaction status
	status = models.CharField(max_length=1, choices=TRANSACTION_STATUSES, default='U')

	# expanded error data in the case that STATUS = 'E'
	error_code = models.IntegerField(default=0)
	error_data = PickledObjectField()

	@property
	def deposit_address(self):
		if 'address' in self.fingerprint:
			return self.fingerprint['address']
		return ''

	@property
	def error_message(self):
		if 'error_message' in self.error_data:
			return self.error_data['error_message']
		return ''

class RecurringOrder(models.Model):
	id = models.CharField(max_length=16, default=crypto.gen_eid, primary_key=True)
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='recurring_orders')
	template = models.ForeignKey('OrderTemplate', related_name='recurring_orders')
	interval = models.IntegerField()
	first_run = models.DateTimeField()
	last_run = models.DateTimeField(auto_now_add=True)


class OrderTemplate(models.Model):
	"""
	Market order templates from which limit orders can be produced.
	"""
	id = models.CharField(max_length=16, default=crypto.gen_eid, primary_key=True)

	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='order_templates')

	currencies = CRYPTOCURRENCIES.items() + CURRENCIES.items()

	withdrawal_payment_method = models.ForeignKey('users.PaymentMethod', related_name='withdrawal_order_templates', null=True)
	deposit_payment_method = models.ForeignKey('users.PaymentMethod', related_name='deposit_order_templates', null=True)

	bid_currency = models.CharField(max_length=3, choices=currencies)
	ask_currency = models.CharField(max_length=3, choices=currencies)	

	type = models.CharField(max_length=1, choices=(('A', 'Ask'), ('B', 'Bid'))) 

	subtotal = models.DecimalField(max_digits=20, decimal_places=10)

class OrderManager(models.Manager):
	def create_data_from_template(self, template, comment='', data={}):
			data['comment'] = comment
			data['bid_currency'] = template.bid_currency
			data['ask_currency'] = template.ask_currency
			exchange_rate = POOLS[getattr(CURRENCIES + CRYPTOCURRENCIES, template.bid_currency)][getattr(CURRENCIES + CRYPTOCURRENCIES, template.ask_currency)].exchange_rate
			data['withdrawal_account'] = template.withdrawal_payment_method.id
			data['deposit_account'] = template.deposit_payment_method.id
			if template.type == 'A':
				data['ask_subtotal'] = template.subtotal
				data['bid_subtotal'] = template.subtotal * exchange_rate
			elif template.type == 'B':
				data['ask_subtotal'] = template.subtotal / exchange_rate
				data['bid_subtotal'] = template.subtotal
			else:
				raise NotImplementedError()
			return(data)

	def create_order(self, ip, user, bid_currency, ask_currency, data, is_reoccuring=False):
		ask_subtotal = Decimal(data['ask_subtotal'])
		bid_subtotal = Decimal(data['bid_subtotal'])
		tx = Transaction.objects.create(
			user=user, comment=data.get('comment', ''),
			is_api=user.use_api, fingerprint={},
			withdrawal_payment_method=PaymentMethod.objects.get(id=data['withdrawal_account']),
			deposit_payment_method=PaymentMethod.objects.get(id=data['deposit_account']),
			ip=ip,
			is_reoccuring=is_reoccuring,
		)
		order = Order.objects.create(
			transaction=tx,
			bid_subtotal=bid_subtotal,
			ask_subtotal=ask_subtotal,
			bid_currency=bid_currency,
			ask_currency=ask_currency,
			ask_fee=settings.CALCULATE_FEE(ask_subtotal, ask_currency),
			bid_fee=settings.CALCULATE_FEE(bid_subtotal, bid_currency),
			exchange_rate=(bid_subtotal / ask_subtotal).quantize(Decimal('1.00000000')),
		)
		tx.save()
		order.save()
		return(order)

# data on the physical exchange of COINS and CURRENCY
class Order(models.Model):
	class Meta:
		ordering = ['-timestamp', '-bid_subtotal', '-ask_subtotal']

	id = models.CharField(max_length=16, default=crypto.gen_eid, primary_key=True)

	# aux data fields - if NULL, implies the order was carried out with Yellowcoin
	transaction = models.OneToOneField(Transaction, related_name='order', blank=True, null=True)

	# time at which the transaction was initialized
	timestamp = models.DateTimeField(default=timezone.now)

	# currencies being used
	#	cf http://www.xe.com/iso4217.php
	currencies = CRYPTOCURRENCIES.items() + CURRENCIES.items()

	# cf. yellowcoin.currencypool.models.CRYPTOCURRENCIES
	bid_currency = models.CharField(max_length=3, choices=currencies)
	ask_currency = models.CharField(max_length=3, choices=currencies)

	# cash will only need three decimal places (one-tenth of a cent)
	#	assuming max amount is 1PetaX
	bid_subtotal = models.DecimalField(max_digits=20, decimal_places=10)
	ask_subtotal = models.DecimalField(max_digits=20, decimal_places=10)
	bid_fee = models.DecimalField(max_digits=20, decimal_places=10)
	ask_fee = models.DecimalField(max_digits=20, decimal_places=10)

	exchange_rate = models.DecimalField(max_digits=20, decimal_places=10)

	objects = OrderManager()

	@property
	def ask_total(self):
		return self.ask_subtotal - self.ask_fee

	@property
	def bid_total(self):
		return self.bid_subtotal + self.bid_fee

	@staticmethod
	def is_cash(currency):
		if currency not in ( abbrev for ( abbrev, _, ) in Order.currencies ):
			raise BadProtocolException()
		return currency not in ( abbrev for ( abbrev, _, )  in CRYPTOCURRENCIES.items() )

	# other logging data

	def delete(self, *args, **kwargs):
		self.transaction.delete()
		super(Order, self).delete(*args, **kwargs)

class TransactionLimit(models.Model):
	user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name='transaction_limits')

	currency = models.CharField(max_length=3, choices=Order.currencies)
	cur_amount = models.DecimalField(max_digits=20, decimal_places=10, null=True)
	max_amount = models.DecimalField(max_digits=20, decimal_places=10, null=True)
	last_reset = models.DateTimeField(default=timezone.now)
	override = models.BooleanField(default=False)

	@property
	def remaining(self):
		return self.max_amount - self.cur_amount

	# tests to see if we can increment the cur_amount
	def test(self, val):
		return (self.cur_amount + val) <= self.max_amount

	# increment the current amount if cur_amount + val < max_amount -- else return False
	def increment(self, val):
		if not self.test(val):
			return False
		self.cur_amount += val
		self.save()
		return True

	def save(self, *args, **kwargs):
		if not self.id:
			self.cur_amount = 0
			self.max_amount = self.user.get_limit(self.currency)
		elif not self.override:
			self.max_amount = self.user.get_limit(self.currency)
		super(TransactionLimit, self).save(*args, **kwargs)
