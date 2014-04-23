class Price():
	def __init__(self, bid, ask, rate, timestamp):
		self.bid_currency = bid
		self.ask_currency = ask
		self.price = rate
		self.timestamp = timestamp
