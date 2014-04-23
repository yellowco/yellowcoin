class Enum(object):
	def __init__(self, **named):
		self.data = named
	def __getattr__(self, name):
		return self.data[name]
	def __getitem__(self, key):
		return self.data[key]
	def __add__(self, other):
		return Enum(**dict(list(self.data.items()) + list(other.data.items())))
	def __iter__(self):
		return self.iteritems()
	def keys(self):
		return self.data.keys()
	def items(self):
		return tuple([(k, v) for (k, v) in self.data.items()])
	def iteritems(self):
		return self.data.iteritems()
CRYPTOCURRENCIES = Enum(BTC='Bitcoin')
CURRENCIES = Enum(USD='United States Dollars')

