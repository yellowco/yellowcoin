# Celery tasks

from __future__ import absolute_import
from yellowcoin.celery import logger
from celery import shared_task
from django.conf import settings
from yellowcoin.transactions.models import Order, Transaction, TransactionLimit, RecurringOrder
from yellowcoin.users.models import User, Profile
from yellowcoin.api.users.views import ResponseParser
from yellowcoin.api.exceptions import VerificationException
from socket import timeout
from bitcoinrpc.exceptions import InvalidAddressOrKey
from yellowcoin.transactions.statuses import status
from decimal import Decimal
from pprint import pformat
from datetime import datetime, timedelta
from yellowcoin.api.exceptions import InsufficientFundsException
from yellowcoin.currencypool.models import POOLS
from balanced_yellowcoin import balanced as payment_network
from django.utils import timezone
from yellowcoin.enums import CRYPTOCURRENCIES, CURRENCIES
import requests
from yellowcoin.api.transactions.serializers import OrderTemplateSerializer
import yellowcoin.users.signals as signals
import logging

logger = logging.getLogger('tasks.audit')

# TODO -- add formatting

# debug

def log(msg):
	message = '%s\t%s' % ( str(timezone.now()), str(msg), )
	logger.info(message)

tx_dump = lambda tx, msg: log('\t'.join(str(x) for x in (
	tx.user.id, tx.id, tx.order.id, tx.status,
	tx.deposit_tx_id, tx.withdrawal_tx_id,
	tx.error_code, tx.error_data.get('error_message', ''), msg, )))

def status_handler(t, status, msg='', aux={}):
	if(aux):
		t.error_data = aux
	t.error_code = status
	t.error_data['error_message'] = msg
	return t

def error_base_handler(t, msg='', aux={}):
	return status_handler(t, status.ERROR_BASE, msg, aux)

def insufficient_funds_handler(t, msg='We\'ve run out of money!'):
	return status_handler(t, status.INSUFFICIENT_FUNDS, msg)

# status.LIMIT_CEILING is a WARNING -- pauses the task at the current stage to be re-checked on next iteration
def limit_ceiling_handler(t, msg='Your daily transaction limit has been reached. This order will be fulfilled once your limit has been reset.'):
	return status_handler(t, status.LIMIT_CEILING, msg=msg)

def info_base_handler(t, msg):
	return status_handler(t, status.INFO_BASE, msg)

def external_transaction_failure_handler(t, msg='The transaction could not be proccessed. Please contact us for further details.', aux={}):
	return status_handler(t, status.EXTERNAL_TRANSACTION_FAILURE, msg=msg, aux=aux)

def awaiting_deposit_handler(t, bid_total, address):
	return status_handler(t, status.AWAITING_DEPOSIT, msg='Send %f coins to %s.' % ( bid_total, address, ))

def success_handler(t):
	t = status_handler(t, status.SUCCESS)
	t.error_data = {}
	return t

# on permanent failure, we may need to return money back into the pool
def reset_pool_handler(t, msg, aux, pool, amount):
	pool.add(amount, t.fingerprint['currency_pool_exchange_rate'])
	return error_base_handler(t, msg, aux)

# resets the transaction limits once per day
@shared_task
def reset_limits():
	for transaction_limit in TransactionLimit.objects.filter(cur_amount__gt=0).all():
		now = timezone.now()
		if (now - transaction_limit.last_reset).days > 1:
			transaction_limit.last_reset = now
			transaction_limit.cur_amount = 0
			transaction_limit.save()

# delete all abandoned transactions
# do not need to call payment_method.unlock() -- abandoned transactions do not affect locked status
@shared_task
def clear_orders():
	abandoned_transactions = Transaction.objects.filter(status='A')
	for t in abandoned_transactions:
		tx_dump(t, 'deleting transaction from database')
		t.order.delete()

# scans recurring orders and adds a new order object if necessary
@shared_task
def execute_recurring_orders():
	now = timezone.now()
	for ro in RecurringOrder.objects.exclude(first_run__gt=now).all():
		if now >= ro.last_run + timedelta(seconds=ro.interval):
			template = ro.template
			a = Order.objects.create_order(False, settings.HOST_IP, template.user, template.bid_currency, template.ask_currency, Order.objects.create_data_from_template(template), is_reoccuring=True)
			ro.last_run = now
			ro.save()

# executes all orders in queue
@shared_task
def execute_orders():
	# get all incomplete transactions, which did not FAIL permanently
	active_transactions = Transaction.objects.exclude(status='C').exclude(status='A').filter(error_code__lt=status.ERROR_BASE)
	active_transactions = sorted(active_transactions, key=lambda x: x.order.timestamp)

	for t in active_transactions:
		# lock the database row to prevent race conditions
		#	cf. http://bit.ly/1meLD8t
		t = Transaction.objects.select_for_update().get(id=t.id)

		# UNINITIALIZED - check the order can be initialized (does not overstep transaction limits)
		if t.status == 'U':
			init(t)
		# INITIALIZED - drain money from the withdrawal account
		elif t.status == 'I':
			drain(t)
		# PENDING - prompt user to send cryptocurrency to Yellowcoin
		#	last status at which the user can cancel a transaction
		elif t.status == 'P':
			prompt(t)
		# QUERIED - waiting confirmation of successful withdrawal
		elif t.status == 'Q':
			check(t)
		# RECEIVED - fill money to the deposit account
		elif t.status == 'R':
			fill(t)
		# DELETED - refund money to the user
		elif t.status == 'D':
			refund(t)

		tx_dump(t, 'executed transaction')

def init(t):
	order = t.order
	t.error_data = {}
	t = success_handler(t)

	# check if transaction has been abandoned
	if (not t.withdrawal_payment_method) or (not t.deposit_payment_method):
		t.status = 'A'
		t = info_base_handler(t, msg='This transaction will never complete, as the end points are not provided.')
		t.save()
		return


	# checking minimum exchange rate which will be fulfilled
	try:
		pool = get_pool(order.bid_currency, order.ask_currency)
		success = (order.bid_subtotal >= pool.get_bid_price(quantity=order.ask_subtotal))
	except InsufficientFundsException:
		t = insufficient_funds_handler(t)
		t.save()
		return

	if success:
		t.status = 'I'
		t = success_handler(t)

		# lock accounts
		t.withdrawal_payment_method.lock()
		t.deposit_payment_method.lock()

	else:
		t = info_base_handler(t, msg='This transaction will be fulfilled when the exchange rate condition is met.')
		t.save()
		return

	# add the order limit objects if they do not yet exist
	try:
		bid_limit = TransactionLimit.objects.get(user=t.user, currency=order.bid_currency)
		bid_limit.save()
	except TransactionLimit.DoesNotExist:
		bid_limit = TransactionLimit.objects.create(user=t.user, currency=order.bid_currency)

	try:
		ask_limit = TransactionLimit.objects.get(user=t.user, currency=order.ask_currency)
		ask_limit.save()
	except TransactionLimit.DoesNotExist:
		ask_limit = TransactionLimit.objects.create(user=t.user, currency=order.ask_currency)

	if not bid_limit.test(order.bid_subtotal) or not ask_limit.test(order.ask_subtotal):
		t = limit_ceiling_handler(t)
		t.save()
		return

	bid_limit.increment(order.bid_subtotal)
	ask_limit.increment(order.ask_subtotal)

	t.save()

def drain(t):
	order = t.order
	withdrawal_payment_method = t.withdrawal_payment_method.get_object(t.user)

	# reserve currency from the currency pool
	try:
		pool = get_pool(order.bid_currency, order.ask_currency)
		t.fingerprint['currency_pool_exchange_rate'] = pool.get_bid_price(quantity=order.ask_subtotal) / order.ask_subtotal
		pool.remove(order.ask_total)
	except NotImplementedError:
		pass
	except InsufficientFundsException:
		t = insufficient_funds_handler(t)
		t.save()
		return

	# payment account interaction
	try:
		( success, tx_id, aux, ) = withdrawal_payment_method.sale(order.bid_total)
		t.withdrawal_tx_id = tx_id
	except Exception as aux:
		success = False

	# response parsing
	if success:
		t = success_handler(t)
		signals.start_transaction.send(sender=None, user=t.user)
		if t.withdrawal_payment_method.foreign_model == 'C':
			t.status = 'P'
			t.fingerprint['address'] = aux['address']
			signals.action_required.send(sender=None, user=t.user, message='Send %f %s to %s.' % (order.bid_total, order.bid_currency, aux['address']))
			t = awaiting_deposit_handler(t, order.bid_total, aux['address'])
		# no further user interaction is necessary if the account is 'BankAccount'
		else:
			t.status = 'Q'

	# rollback changes
	else:
		t = reset_pool_handler(t, 'Something went wrong while withdrawing from your account. Please contact us.', aux, pool, order.ask_total)

	t.save()

# further user interaction is required -- currently, only handles CryptoAccounts, with currency = BTC
def prompt(t):
	order = t.order
	withdrawal_payment_method = t.withdrawal_payment_method.get_object(t.user)

	expire = True
	try:
		unconf = settings.BTC_CONN.getreceivedbyaddress(t.fingerprint['address'], minconf=0)
		amount = settings.BTC_CONN.getreceivedbyaddress(t.fingerprint['address'], minconf=settings.BTC_MINCONF)
		if amount >= order.bid_total:
			expire = False

			# ensure that the minimum exchange rate is still valid -- delay otherwise
			pool = get_pool(order.bid_currency, order.ask_currency)
			success = (order.bid_subtotal >= pool.get_bid_price(quantity=order.ask_subtotal))

			# Yellowcoin is ready to honor the contract and send appropriate currency to the user
			if success:
				tx_data = settings.BTC_CONN.listtransactions(settings.BTC_ACCT, address=t.fingerprint['address'], count=1)[0]
				del t.fingerprint['address']
				# TODO - check that tx_data.address == t.fingerprint['address']
				#	if not, raise INFO error
				# tx_id is the LAST transaction that took place
				t.withdrawal_tx_id = tx_data.txid
				t.status = 'R'

				t = success_handler(t)

			# need to ensure that the pool rate is still valid before honoring the contract
			else:
				t = info_base_handler(t, msg='This transaction will be fulfilled when the exchange rate condition is met.')

			# refund any extra funds received
			if amount > order.bid_total:
				# TODO - set tx_fee = 0 for the refund
				# do not need to catch Exception -- cryptocurrencies do not raise Exceptions
				try:
					withdrawal_payment_method.credit(float(Decimal(amount) - order.bid_total))
					t.error_code = status.WITHDRAWAL_OVERFLOW
					t.error_data['tx_data'] = tx_data
					t.error_data['error_message'] = 'We have refunded %f coins to your provided withdrawal address.' % ( float(Decimal(amount) - order.bid_total), )			
				except Exception as aux:
					pass

		elif amount > 0:
			# incomplete deposits
			t = info_base_handler(t, 'Send %f coins to %s (%f received, %f confirmed).' % ( order.bid_total, t.fingerprint['address'], unconf, amount, ))

	except InvalidAddressOrKey:
		error_base_handler(t, msg='There was an error with the transaction. Please contact us.', aux=t.error_data)
	except timeout:
		pass
	
	# we will mark the transaction as invalid (abandoned) if the user doesn't send us the required currency within the specified time period
	#	the transaction will be marked for deletion and hidden from the user
	if expire:
		if (timezone.now() - t.order.timestamp).total_seconds() > settings.TIMEOUT_SECONDS:
			t.status = 'A'
			t.error_code = status.TIMEOUT_ERROR
		# refund money that has been sent thusfar
		# exceptions will not be raised for cryptocurrencies
		try:
			withdrawal_payment_method.credit(float(amount))
		except Exception as aux:
			pass

	if t.error_code >= status.ERROR_BASE:
		try:
			get_pool(order.bid_currency, order.ask_currency).add(order.ask_subtotal, t.fingerprint['currency_pool_exchange_rate'])
		except NotImplementedError:
			pass

	t.save()

def check(t):
	order = t.order
	withdrawal_payment_method = t.withdrawal_payment_method.get_object(t.user)

	if t.withdrawal_payment_method.foreign_model == 'P':
		payment_network_tx = payment_network.Transaction.retrieve(id=t.withdrawal_tx_id)

		# possible that the PaymentNetwork transaction cannot be queried yet (i.e. not added to foreign database)
		if not payment_network_tx:
			return

		# successful action status
		payment_network_status = 'succeeded'

		# PaymentNetwork tx_id query will return success if amount has been successfully pulled from the user
		if payment_network_tx.status == payment_network_status:
			t.status = 'R'
			t = success_handler(t)
		elif payment_network_tx.status == 'failed':
			t = external_transaction_failure_handler(t, payment_network_tx)
		else:
			t = info_base_handler(t, msg='Your transaction is currently in progress (status: %s)' % (payment_network_tx.status))

	t.save()

def fill(t):
	order = t.order
	deposit_payment_method = t.deposit_payment_method.get_object(t.user)

	# payment account interaction
	try:
		( success, tx_id, aux, ) = deposit_payment_method.credit(float(order.ask_total))
		t.deposit_tx_id = tx_id
	except Exception as aux:
		success = False

	# response parsing
	if success:
		t.status = 'C'
		try:
			get_pool(order.bid_currency, order.ask_currency).add(order.ask_subtotal, t.fingerprint['currency_pool_exchange_rate'])
		except NotImplementedError:
			pass
		t = success_handler(t)

		t.fingerprint = {}

		signals.end_transaction.send(sender=None, user=t.user)

		# unlock accounts
		t.withdrawal_payment_method.unlock()
		t.deposit_payment_method.unlock()
	else:
		t = error_base_handler(t, msg='Something went wrong while depositing into your account. Please contact us.', aux=aux)

	t.save()

def get_pool(bid, ask):
	return POOLS[getattr(CRYPTOCURRENCIES + CURRENCIES, bid)][getattr(CRYPTOCURRENCIES + CURRENCIES, ask)]

def refund(t):
	order = t.order
	withdrawal_payment_method = t.withdrawal_payment_method.get_object(t.user)

	if 'currency_pool_exchange_rate' not in t.fingerprint:
		t = success_handler(t)
		t.status = 'A'
		t.save()
		return

	# rollback changes, if the pool has already been committed
	try:
		get_pool(order.bid_currency, order.ask_currency).add(order.ask_subtotal, t.fingerprint['currency_pool_exchange_rate'])
	except NotImplementedError:
		pass

	# refund money
	try:
		( success, tx_id, aux, ) = withdrawal_payment_method.credit(float(order.bid_total))
	except Exception as aux:
		success = False

	# response parsing
	if success:
		t = success_handler(t)
		t.status = 'A'
	else:
		t.error_code = status.ERROR_BASE
		aux['error_message'] = 'Something went wrong while depositing into your account. Please contact us.'
		t.error_data = aux		

	t.save()
