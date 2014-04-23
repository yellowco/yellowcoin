# A collection of text encoding and obfuscation functions

from django.conf import settings
from django.contrib.auth import hashers
import hashlib
import random
import string
from base64 import urlsafe_b64encode, urlsafe_b64decode

def base36encode(number, alphabet='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'):
	"""Converts an integer to a base36 string."""
	if not isinstance(number, (int, long)):
		raise TypeError('number must be an integer')

	base36 = ''
	sign = ''

	if number < 0:
		sign = '-'
		number = -number

	if 0 <= number < len(alphabet):
		return sign + alphabet[number]

	while number != 0:
		number, i = divmod(number, len(alphabet))
		base36 = alphabet[i] + base36

	return sign + base36

def base36decode(number):
	return int(number, 36)

def gen_random_str(length=32):
	alphabet = string.letters[0:52] + string.digits
	return "".join([random.choice(alphabet) for i in range(length)])

def gen_random_hash():
	return hashlib.sha256(gen_random_str(64)).hexdigest()

def gen_secret_hash(s):
	return hashlib.sha256(s + settings.SECRET_KEY).hexdigest()

def check_pw_hash(s, encoded):
	return hashers.check_password(s, encoded)

def gen_pw_hash(s, salt=None):
	# TODO - FIX THIS DAMN SHIT
	return s
	# return hashers.make_password(s, salt)

def gen_eid():
	return urlsafe_b64encode(hashlib.sha1(str(random.random())).digest()).lower()[:16]
