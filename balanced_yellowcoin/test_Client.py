from balanced import Config
from balanced import Client
import unittest
import datetime
import time

class ClientTest(unittest.TestCase):
	def setUp(self):
		Config.config(key='ak-test-2J2vHkB6NERu57mM6vbOMylbd0X5TJSgG')

	def test_client(self):
		count = len(Client.all())
		self.assertGreater(count, 0)
		client = Client.create()
		client.billing_address.first_name = 'Kevin'
		client.billing_address.last_name = 'Wang'
		client.email = 'kevmo314@gmail.com'
		client.save()
		self.assertIsNotNone(client.id, "Client did not save properly on the server")
		retrieved = Client.retrieve(client.id)
		self.assertIsNotNone(retrieved, "Could not retrieve the client from the server")
		self.assertEqual(retrieved.name, "Kevin Wang", "Name attribute not correctly retrieved from the server")
		self.assertEqual(retrieved.billing_address.first_name, "Kevin")
		self.assertEqual(retrieved.billing_address.last_name, "Wang")
		self.assertEqual(retrieved.email, client.email, "Email attribute not retrieved from the server")
		self.assertIsNone(Client.retrieve(-1), "An invalid client was returned from the server")
		self.assertEqual(len(Client.all()), count + 1)
		id = client.id
		client.email = 'newemail@mail.com'
		self.assertEqual(client.save().id, id, "The server created a new id instead of updating the existing one")
		self.assertEqual(Client.retrieve(id).email, client.email, "Email attribute was not updated")
		client.delete()
		self.assertIsNone(Client.retrieve(id), "Client was not deleted from the server")
		self.assertEqual(len(Client.all()), count)

	def test_partial_client_name(self):
		client = Client.create()
		client.billing_address.first_name = 'Kevin'
		client.email = 'kevmo314@gmail.com'
		client.save()
		self.assertEqual(Client.retrieve(client.id).name, "Kevin", "Name attribute not correctly retrieved from the server")
		client.delete()
		client = Client.create()
		client.billing_address.last_name = 'Kevin'
		client.email = 'kevmo314@gmail.com'
		client.save()
		self.assertEqual(Client.retrieve(client.id).name, "Kevin", "Name attribute not correctly retrieved from the server")
		client.delete()
		client = Client.create()
		client.email = 'kevmo314@gmail.com'
		client.save()
		self.assertEqual(Client.retrieve(client.id).name, "", "Name attribute not correctly retrieved from the server")
		client.delete()

if __name__ == '__main__':
	unittest.main()
