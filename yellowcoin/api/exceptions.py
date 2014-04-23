from rest_framework.views import exception_handler
from rest_framework.exceptions import APIException

class GenericException(APIException):
	def __init__(self, detail=None, status=500):
		self.status_code = status
		self.detail = detail

class BankValidationError(Exception):
	pass

class InsufficientFundsException(Exception):
	pass

# raised on questionable accounts
#	cf http://bit.ly/1c1G4mY
class VerificationException(Exception):
	pass

# if a given currency is neither crypto nor cash
#	e.g. 'FAKE' is not 'BTC' and not 'USD'
class BadProtocolException(Exception):
	pass

# if given payment method cannot be deleted yet
class LockedError(Exception):
	pass

def yellowcoin_exception_handler(exception):
	response = exception_handler(exception)
	if response is not None:
		if not response.data['detail']:
			response.data.pop('detail', None)
		else:
			response.data['status'] = response.status_code
	return response
