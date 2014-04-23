import random

class EmulatedBitcoinConnection(object):
	def __init__(self):
		self._addresses = {}
		self._transactions = {}

	def getnewaddress(self, account=None):
		address = ''.join(random.choice('abcdef1234567890') for x in range(16))
		self._addresses[address] = []
		return address

	def getreceivedbyaddress(self, address, minconf=0):
		s = 0
		if address in self._addresses:
			for transaction in self._addresses[address]:
				if transaction.confirmations >= minconf and transaction.category == 'receive':
					s = s + transaction.amount
		return s

	def validateaddress(self, validateaddress):
		return AddressValidation(validateaddress in self._addresses,
			True, validateaddress)

	def listtransactions(self, account=None, count=-1, from_=0, address=None):
		if count == -1:
			return self._addresses[address][from_:]
		else:
			return self._addresses[address][from_:(from_+count)]

	def gettransaction(self, txid):
		return self._transactions[txid] if txid in self._transactions else None

	def sendtoaddress(self, bitcoinaddress, amount, minconf=1, comment=None, comment_to=None):
		return self.sendfrom(
			fromaccount=None,
			tobitcoinaddress=bitcoinaddress,
			amount=amount,
			minconf=minconf,
			comment=comment,
			comment_to=comment_to)
	
	def sendfrom(self, fromaccount, tobitcoinaddress, amount, minconf=1, comment=None, comment_to=None):
		receive = TransactionInfo(
			amount=amount,
			to=comment_to,
			message=comment,
			address=tobitcoinaddress,
			category='receive'
		)
		if tobitcoinaddress not in self._addresses:
			self._addresses[tobitcoinaddress] = []
		self._addresses[tobitcoinaddress].append(receive)
		self._transactions[receive.txid] = receive
		return receive.txid

class TransactionInfo(object):
	def __init__(self, **kwargs):
		self.account = kwargs.get('account', None)
		self.address = kwargs.get('address', '')
		self.category = kwargs.get('category', '')
		self.amount = kwargs.get('amount', 0)
		self.fee = kwargs.get('fee', 0)
		self.confirmations = kwargs.get('confirmations', 0)
		self.txid = kwargs.get('txid', ''.join(random.choice('abcdef12345567890') for x in range(8)))
		self.otheraccount = kwargs.get('otheraccount', None)
		self.message = kwargs.get('message', '')
		self.to = kwargs.get('to', None)

	def __str__(self):
		return "%s %s" % (self.txid, self.confirmations)
class AddressValidation(object):
	def __init__(self, isvalid, ismine, address):
		self.isvalid = isvalid
		self.ismine = ismine
		self.address = address
