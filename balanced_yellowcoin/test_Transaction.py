from balanced import Config
from balanced import Client
from balanced import BankAccount
from balanced import Transaction
import unittest
import datetime
import time

class TransactionTest(unittest.TestCase):
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
		client.save()
		client.add_payment_method(account)
		self.assertTrue(account.validate(0.01,0.01))

		(success, txid, aux) = account.sale(1)
		self.assertTrue(success)
		self.assertIsNotNone(txid)
		transactions = Transaction.find_all_by_client_id(client.id)
		self.assertTrue(len(transactions), 1)
		self.assertEqual(transactions[0].status, 'succeeded')
		self.assertIsNotNone(transactions[0].id)
		self.assertIsNotNone(Transaction.retrieve(transactions[0].id))

		(success, txid, aux) = account.credit(1)
		self.assertTrue(success)
		self.assertIsNotNone(txid)
		transactions = Transaction.find_all_by_client_id(client.id)
		self.assertTrue(len(transactions), 2)
		self.assertEqual(transactions[0].status, 'succeeded')
		self.assertIsNotNone(transactions[1].id)
		self.assertIsNotNone(Transaction.retrieve(transactions[1].id))

		self.assertRaises(Exception, lambda:account.sale(-1))
		self.assertRaises(Exception, lambda:account.credit(-1))
		

if __name__ == '__main__':
	unittest.main()
