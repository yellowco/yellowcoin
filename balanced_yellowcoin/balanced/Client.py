from .Transaction import Transaction
from .Address import Address
from .BankAccount import BankAccount
import balanced

class Client(object):
	def __init__(self, customer=None):
		self.billing_address = Address()
		self.shipping_address = Address()
		self.customer = customer
		if customer != None:
			self._save_addresses()

	def _load_addresses(self):
		if not self.customer or not hasattr(self.customer, 'id') or not self.customer.id: # object not yet saved
			return
		if self.billing_address.first_name and self.billing_address.last_name:
			self.customer.name = "%s %s" % (self.billing_address.first_name, self.billing_address.last_name)
		elif self.billing_address.first_name or self.billing_address.last_name:
			self.customer.name = "%s" % (self.billing_address.first_name or self.billing_address.last_name)
		else:
			self.customer.name = ""
		self.customer.address['line1'] = self.billing_address.street1
		self.customer.address['line2'] = self.billing_address.street2
		self.customer.address['city'] = self.billing_address.city
		self.customer.address['state'] = self.billing_address.state
		self.customer.address['postal_code'] = self.billing_address.postal
		if self.billing_address.country:
			self.customer.address['country_code'] = self.billing_address.country
		self.customer.phone = self.billing_address.phone

	def _save_addresses(self, target=None):
		if not target:
			self._save_addresses(self.billing_address)
			self._save_addresses(self.shipping_address)
		else:
			if self.customer.name:
				target.first_name = self.customer.name.partition(' ')[0]
				target.last_name = self.customer.name.partition(' ')[2]
			else:
				target.first_name = None
				target.last_name = None
			target.street1 = self.customer.address.get('line1', None)
			target.street2 = self.customer.address.get('line2', None)
			target.city = self.customer.address.get('city', None)
			target.state = self.customer.address.get('state', None)
			target.postal = self.customer.address.get('postal_code', None)
			target.country = self.customer.address.get('country_code', None)
			target.phone = self.customer.phone

	def save(self):
		self._load_addresses()
		self.customer.save()
		self._save_addresses()
		return self

	def delete(self):
		self.customer.delete()
		return self
	
	def add_payment_method(self, account):
		self.save()
		account._load_customer_data(self)
		account.save()
		#TODO: fix this to be more accurate. associate_to_customer isn't working
		account.links = {'customer':self.customer.href}
		account.save()
		account.account.verify()
		return self

	@property
	def bank_accounts(self):
		accounts = []
		for account in self.customer.bank_accounts:
			accounts.append(BankAccount(account))
		return accounts

	@property
	def payment_methods(self):
		return self.bank_accounts

	def __getattr__(self, key):
		return getattr(self.customer, key)

	def __setattr__(self, key, value):
		if 'customer' not in self.__dict__ or key in self.__dict__:
			self.__dict__[key] = value
		else:
			setattr(self.__dict__['customer'], key, value)

	@staticmethod
	def all():
		customers = balanced.Customer.query.pagination
		data = []
		# looks like there's a bug... manually work around it.
		# TODO: figure out what's up.
		for start in range(0, customers.count()):
			page = customers._page(start, customers.size)
			for customer in page.items:
				data.append(Client(customer))
		return data

	@staticmethod
	def create(**kwargs):
		client = Client()
		client.customer = balanced.Customer(**kwargs)
		client.save() # this kind of sucks, but done to populate with default data
		return client

	@staticmethod
	def retrieve(id):
		try:
			return Client(balanced.Customer.fetch('/customers/%s' % id))
		except balanced.exc.HTTPError as error:
			if error.status_code == 404:
				return None
			else:
				raise

	@property
	def transactions(self):
		if self.customer == None:
			return []
		return Transaction.find_all_by_client_id(self.id)
