import unittest
from emulator import EmulatedBitcoinConnection

class BitcoinEmulatorTest(unittest.TestCase):
	def test_emulator(self):
		emulator = EmulatedBitcoinConnection()
		address = emulator.getnewaddress()
		self.assertIsNotNone(address)
		self.assertEqual(emulator.getreceivedbyaddress(address), 0)
		self.assertTrue(emulator.validateaddress(address).isvalid)
		self.assertFalse(emulator.validateaddress('asdf').isvalid)
		self.assertEqual(len(emulator.listtransactions(address=address)), 0)
		emulator.sendfrom(
			fromaccount=None,
			tobitcoinaddress=address,
			amount=1.0
		)
		self.assertEqual(emulator.getreceivedbyaddress(address), 1.0)
		self.assertEqual(len(emulator.listtransactions(address=address)), 1)
		self.assertEqual(emulator.getreceivedbyaddress(address=address, minconf=4), 0)
		transactions = emulator.listtransactions(address=address)
		transactions[0].confirmations = 5
		txid = emulator.sendfrom(
			fromaccount=None,
			tobitcoinaddress=address,
			amount=2.0
		)
		emulator.gettransaction(txid).confirmations = 3
		self.assertEqual(emulator.getreceivedbyaddress(address=address, minconf=4), 1.0)
		self.assertEqual(emulator.getreceivedbyaddress(address=address, minconf=3), 3.0)
