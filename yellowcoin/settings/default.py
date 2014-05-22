from yellowcoin.settings.contrib import *

MAX_USERS = 0

# if a pending order awaiting crypto currency has not received any money in TIMEOUT_SECONDS, abandon transaction and mark for deletion
#	invoked in transactions/tasks.py
TIMEOUT_SECONDS = 48 * 3600

MIN_USD_TX = 0.00

from decimal import Decimal
FEE_RATIO = Decimal('0.01')

REFERRAL_BONUS = 0.005 # in BTC

def CALCULATE_FEE(val, currency):
	if currency == 'BTC':
		return Decimal('0')
	elif currency == 'USD':
		return max(FEE_RATIO * val, Decimal('7'))
	return 0
