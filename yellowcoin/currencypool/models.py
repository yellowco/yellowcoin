from django.db import models, transaction
from django.utils import timezone
from random import random
from decimal import Decimal
from yellowcoin.api.exceptions import InsufficientFundsException
from yellowcoin.enums import *
import requests

class CurrencyAcquisition(models.Model):
	currency = models.CharField(max_length=3, choices=CRYPTOCURRENCIES.items(), default=CRYPTOCURRENCIES.BTC)
	quantity = models.DecimalField(max_digits=20, decimal_places=10)
	price_per_unit = models.DecimalField(max_digits=20, decimal_places=10)
	timestamp = models.DateTimeField(default=timezone.now)

class CurrencyPool(object):
	def __init__(self, currency=CRYPTOCURRENCIES.BTC):
		self.currency = currency

	@property
	def _queryset(self):
		return CurrencyAcquisition.objects.filter(currency=self.currency)

	@property
	def balance(self):
		return self._queryset.aggregate(models.Sum('quantity'))

	@property
	def exchange_rate(self):
		if self._queryset.exists():
			return Decimal(self._queryset.order_by('price_per_unit')[0].price_per_unit)
		raise InsufficientFundsException('No money')

	def add(self, quantity, price_per_unit):
		CurrencyAcquisition(currency=self.currency,
			quantity=quantity,
			price_per_unit=price_per_unit).save()

	def get_bid_price(self, quantity=1):
		acquisitions = self._queryset.order_by('price_per_unit').all()

		if quantity == 0:
			return Decimal(0) # special case

		quantity = Decimal(quantity)

		total_quantity = Decimal(0)
		total_cost = Decimal(0)

		for acquisition in acquisitions:
			if total_quantity + acquisition.quantity >= quantity:
				# this acquisition is the terminating acquisition
				partial_quantity = total_quantity + acquisition.quantity - quantity
				total_cost = total_cost + (acquisition.quantity - partial_quantity) * acquisition.price_per_unit
				return round(total_cost, 2)
			else:
				total_quantity = total_quantity + acquisition.quantity
				total_cost = total_cost + acquisition.quantity * acquisition.price_per_unit
		if total_quantity == quantity:
			return round(total_cost, 2)
		request = requests.get('https://www.bitstamp.net/api/ticker/')
		if request.status_code == 200:
			return Decimal(request.json()['bid']) / quantity
		raise InsufficientFundsException('No more currency available')

	@transaction.atomic
	def remove(self, quantity):
		acquisitions = self._queryset.order_by('price_per_unit').select_for_update()

		total_quantity = Decimal(0)

		for acquisition in acquisitions:
			if total_quantity + acquisition.quantity >= quantity:
				partial_quantity = total_quantity + acquisition.quantity - quantity
				if partial_quantity == 0:
					# remove it too
					acquisition.delete()
				else:
					# update
					acquisition.quantity = partial_quantity
					acquisition.save()
				return
			else:
				total_quantity = total_quantity + acquisition.quantity
				acquisition.delete()
		raise InsufficientFundsException('No more currency available')

class BitcoinCurrencyPool(CurrencyPool):
	def __init__(self):
		super(BitcoinCurrencyPool, self).__init__(CRYPTOCURRENCIES.BTC)

class InverseCurrencyPool(CurrencyPool):
	def __init__(self, parent):
		self.parent = parent

	@property
	def balance(self):
		return self.get_bid_price(self.parent.balance)

	@property
	def _queryset(self):
		return CurrencyAcquisition.objects.filter(currency=self.parent.currency)

	@property
	def exchange_rate(self):
		if self._queryset.exists():
			return Decimal(1.0) / Decimal(self._queryset.order_by('price_per_unit')[0].price_per_unit)
		raise InsufficientFundsException('No money')

	def get_bid_price(self, quantity=1):
		# TODO: This needs to be improved
		return self.exchange_rate * quantity

	def add(self, quantity, price_per_unit):
		raise NotImplementedError('This is an inverse currency pool. It cannot be modified.')

	def remove(self, quantity):
		raise NotImplementedError('This is an inverse currency pool. It cannot be modified.')	

USDBTC = BitcoinCurrencyPool()
BTCUSD = InverseCurrencyPool(USDBTC)

POOLS = {
	CURRENCIES.USD:{
		CRYPTOCURRENCIES.BTC:USDBTC
	},
	CRYPTOCURRENCIES.BTC:{
		CURRENCIES.USD:BTCUSD
	}
}
