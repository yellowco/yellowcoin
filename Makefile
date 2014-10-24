CONFIG?=development
TEST?='yellowcoin.transactions.tests.TestTransactions'

SETTINGS=yellowcoin.settings.$(CONFIG)
test:
	./manage.py test --settings=$(SETTINGS) $(TEST) 2>&1 | tee results.log

run:
	./manage.py runserver 0:8000 --settings=$(SETTINGS)

sync:
	./manage.py migrate --settings=$(SETTINGS)
