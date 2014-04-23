from decimal import Decimal
import balanced

class BankAccount(object):
	CHECKING = 'checking'
	SAVINGS = 'savings'
	def __init__(self, account=None):
		self.account = account

	def sale(self, amount=0, appears_on_statement_as='Yellowcoin', description='Trade'):
		debit = self.account.debit(amount=int(Decimal(amount) * 100), appears_on_statement_as=appears_on_statement_as, description=description)
		return (debit.failure_reason is None, debit.id, debit)

	def authorization(self, amount):
		raise NotImplementedError("Balanced does not have this method implemented.")

	def credit(self, amount):
		credit = self.account.credit(int(Decimal(amount) * 100))
		return (credit.failure_reason is None, credit.id, credit)

	def force(self, amount):
		raise NotImplementedError("Balanced does not have this method implemented.")

	def verify(self, amount):
		raise NotImplementedError("Balanced does not have this method implemented.")

	def save(self):
		self.account.save()
		return self

	def delete(self):
		self.account.delete()
		return self

	def associate_to_customer(self, customer):
		self.account.associate_to_customer(customer)
		self.account.verify()
		return self

	def validate(self, amount_1, amount_2):
		validation = self.account.bank_account_verifications.first()
		if not validation:
			self.account = BankAccount.retrieve(id=self.id)
			validation = self.account.bank_account_verifications.first()
		try:
			validation.confirm(int(Decimal(amount_1)*100), int(Decimal(amount_2)*100))
			return True
		except Exception as e:
			if hasattr(e, 'status_code') and e.category_code == 'bank-account-authentication-failed':
				return False
			else:
				raise e

	def _load_customer_data(self, client):
		self.name = "%s %s" % (client.billing_address.first_name, client.billing_address.last_name)

	def __getattr__(self, key):
		if hasattr(self.__dict__['account'], key):		
			return getattr(self.__dict__['account'], key)
		else:
			return self.__dict__['account'].meta[key]

	def __setattr__(self, key, value):
		if 'account' not in self.__dict__ or key == 'account':
			self.__dict__[key] = value
		else:
			setattr(self.__dict__['account'], key, value)

	@staticmethod
	def create(**kwargs):
		if 'type' in kwargs:
			kwargs['account_type'] = kwargs.pop('type')
		return BankAccount(balanced.BankAccount(**kwargs))

	@staticmethod
	def retrieve(id):
		return BankAccount(balanced.BankAccount.fetch('/bank_accounts/%s' % id))
		
