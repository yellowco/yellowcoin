from yellowcoin.settings.contrib import *
from balanced_yellowcoin import balanced

balanced.Config.config(key='ak-test-2J2vHkB6NERu57mM6vbOMylbd0X5TJSgG')

MAX_USERS = -1

# if a pending order awaiting crypto currency has not received any money in TIMEOUT_SECONDS, abandon transaction and mark for deletion
#	invoked in transactions/tasks.py
TIMEOUT_SECONDS = 48 * 3600

MIN_USD_TX = 0.00

from decimal import Decimal
FEE_RATIO = Decimal('0.01')

def CALCULATE_FEE(val, currency):
	if currency == 'BTC':
		return 0
	elif currency == 'USD':
		return max(val * FEE_RATIO, 7)
	return 0
