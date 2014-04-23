from balanced import Config
from balanced import Client
from balanced import BankAccount
import unittest
import datetime
import time

class PaymentMethodTest(unittest.TestCase):
	def setUp(self):
		Config.config(key='ak-test-2J2vHkB6NERu57mM6vbOMylbd0X5TJSgG')

	def test_bindable(self):
		client = Client.create()
		client.billing_address.first_name = 'Kevin'
		client.billing_address.last_name = 'Wang'
		client.email = 'kevmo314@gmail.com'
		account = BankAccount.create(
			account_holder='John Customer',
			account_number='1234567845390',
			routing_number='253271806',
			type=BankAccount.CHECKING)
		account.meta = {'random_data':'yes'}
		client.add_payment_method(account)
		id = client.save().id
		n = Client.retrieve(id=id)
		self.assertIsNotNone(n, "Could not retrieve client %s" % id)
		self.assertEqual(n.payment_methods[0].random_data, 'yes', "The arbitrary data did not save correctly")
		self.assertFalse(account.validate(0.01,0.02))
		self.assertFalse(BankAccount.retrieve(id=account.id).can_debit)
		self.assertTrue(account.validate(0.01,0.01))
		self.assertTrue(BankAccount.retrieve(id=account.id).can_debit)
		self.assertEqual(account.debits.count(), 0)
		self.assertRaises(Exception, lambda: account.debit(-1))
		self.assertTrue(account.debit(1))
		self.assertEqual(account.debits.count(), 1)
		self.assertEqual(account.credits.count(), 0)
		self.assertRaises(Exception, lambda: account.credit(-1))
		self.assertTrue(account.credit(1))
		self.assertEqual(account.credits.count(), 1)

	def test_fail_validation(self):
		client = Client.create()
		client.billing_address.first_name = 'Kevin'
		client.billing_address.last_name = 'Wang'
		client.email = 'kevmo314@gmail.com'
		account = BankAccount.create(
			account_holder='John Customer',
			account_number='1234567845390',
			routing_number='253271806',
			type=BankAccount.CHECKING)
		client.add_payment_method(account)
		id = client.save().id
		n = Client.retrieve(id=id)
		self.assertFalse(account.validate(1,2))
		self.assertFalse(account.validate(1,2))
		self.assertFalse(account.validate(1,2))
		self.assertRaises(Exception, lambda: account.validate(1,2))


if __name__ == '__main__':
	unittest.main()
