import balanced

class Transaction(object):
	def __init__(self, transaction=None):
		self.transaction = transaction

	def __getattr__(self, key):
		if hasattr(self.__dict__['transaction'], key):		
			return getattr(self.__dict__['transaction'], key)
		else:
			return self.__dict__['transaction'].meta[key]
	
	@staticmethod
	def retrieve(id):
		try:
			return Transaction(balanced.Debit.fetch('/debits/%s' % id))
		except Exception as e:
			if e.status_code != 404:
				raise e
		try:
			return Transaction(balanced.Credit.fetch('/credits/%s' % id))
		except Exception as e:
			if e.status_code != 404:
				raise e
		return None

	@staticmethod
	def find_all_by_client_id(id):
		customer = balanced.Customer.fetch('/customers/%s' % id)
		objs = []
		for tx in customer.debits.all() + customer.credits.all():
			objs.append(Transaction(tx))
		return objs
