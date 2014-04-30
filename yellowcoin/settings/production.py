from yellowcoin.settings.default import *
from urllib import quote

BROKER_URL = 'sqs://' + quote('AKIAIUJ4M64I3EGSNGNQ:bNPldWAN7L0e+d5hjzIZY6qOUNbm6iOAqOvJq9RT') + '@'
BROKER_TRANSPORT_OPTIONS = { 'region' : 'us-west-2' }
