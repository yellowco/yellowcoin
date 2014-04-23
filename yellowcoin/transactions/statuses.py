# list of transaction error codes

class status():
	SUCCESS = 0

	INFO_BASE = 100					# notices to the user
	WARNING_BASE = 200				# unspecified warning
	ERROR_BASE = 500				# unspecified error

	# info
	WITHDRAWAL_OVERFLOW = 110			# overdrawn from the withdrawal account - refunded to address provided
	INSUFFICIENT_FUNDS = 120			# yellowcoin ran out of funds
	AWAITING_DEPOSIT = 130				# waiting for user to deposit crytocurrency into the address provided

	# warnings
	LIMIT_CEILING = 210				# has reached bid limit for the day - must wait until the limit is reset

	# errors - permanent failure
	ACCOUNT_NOT_TRUSTED = 510			# the account cannot be trusted
	EXTERNAL_TRANSACTION_ERROR = 520		# there was an error with a deposit or withdrawal from a bank or credit card, etc.
	TIMEOUT_ERROR = 530				# no money has been received in the designated crypto currency account within TIMEOUT_SECONDS
