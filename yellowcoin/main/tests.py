from django.test import TestCase
from django.test.client import Client

class MainTestCase(TestCase):
	def test_pages(self):
		self.assertEqual(Client().get('/').status_code, 200)
		self.assertEqual(Client().get('/api/').status_code, 200)
		self.assertEqual(Client().get('/contact-us/').status_code, 200)
		self.assertEqual(Client().get('/about/').status_code, 200)
