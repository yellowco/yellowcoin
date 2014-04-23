from django.test import TestCase

from yellowcoin.currencypool.models import POOLS
from yellowcoin.enums import *

from decimal import Decimal

class TestCurrencyPool(TestCase):
	def setUp(self):
		self.pool = POOLS[CURRENCIES.USD][CRYPTOCURRENCIES.BTC]
		self.inverse_pool = POOLS[CRYPTOCURRENCIES.BTC][CURRENCIES.USD]
	def test_exchange_rate(self):
		self.pool.add(10, 5)
		self.assertAlmostEqual(self.pool.exchange_rate, 5)
		self.assertAlmostEqual(self.inverse_pool.exchange_rate, Decimal('0.2'))
		self.assertAlmostEqual(self.pool.get_bid_price(10), 50)
		self.assertAlmostEqual(self.inverse_pool.get_bid_price(5), 1)
		self.pool.add(10, 35)
		self.assertAlmostEqual(self.pool.exchange_rate, 5)
		self.assertAlmostEqual(self.inverse_pool.exchange_rate, Decimal('0.2'))
		self.assertAlmostEqual(self.pool.get_bid_price(20), 400)
		self.assertAlmostEqual(self.inverse_pool.get_bid_price(20), 4)
		self.pool.remove(5)
		self.assertAlmostEqual(self.pool.exchange_rate, 5)
		self.assertAlmostEqual(self.inverse_pool.exchange_rate, Decimal('0.2'))
		self.assertAlmostEqual(self.pool.get_bid_price(10), 200)
		self.assertAlmostEqual(self.inverse_pool.get_bid_price(20), 4)
		self.assertAlmostEqual(self.pool.get_bid_price(15), 375)
		self.assertAlmostEqual(self.inverse_pool.get_bid_price(25), 5)
		self.pool.remove(5)
		self.assertAlmostEqual(self.pool.exchange_rate, 35)
		self.assertAlmostEqual(self.inverse_pool.exchange_rate, Decimal(1.0 / 35))
		self.assertAlmostEqual(self.pool.get_bid_price(10), 350)
		self.assertAlmostEqual(self.inverse_pool.get_bid_price(35), 1)
	
