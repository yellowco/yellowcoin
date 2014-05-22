from django.conf import settings
from decimal import Decimal

class Fee():
	def __init__(self, bid, ask, bid_val, ask_val):
		self.bid_currency = bid
		self.ask_currency = ask
		self.bid_val = Decimal(bid_val)
		self.ask_val = Decimal(ask_val)
		self.bid_fee = settings.CALCULATE_FEE(self.bid_val, bid)
		self.ask_fee = settings.CALCULATE_FEE(self.ask_val, ask)
