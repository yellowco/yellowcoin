# cf. http://bit.ly/1l1FqK7
#	cf. http://bit.ly/1k86DwD
#	cf. http://bit.ly/19BrB2F
from bitcoinrpc import connect_to_remote, connect_to_local

# btc_conn = connect_to_remote('13PgfhMMjgBT9m3uxP3UaQLQdHnZgBQK8U', '95o6YnhXkbv1fcmqgUp4Qgs8wGqWHgMncntehz2HU9z6', host='rpc.blockchain.info', port=443, use_https=True)
BTC_CONN = connect_to_remote('Yellowcoin', 't4L3DRgeAb', host='54.186.24.74')

# number of confirmation on the transaction before we accept the transaction as true
BTC_MINCONF = 4
# cf. http://bit.ly/18Y8cZe
BTC_ACCT = 'BTC_ACCT'
