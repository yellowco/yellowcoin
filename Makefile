SETTINGS?=yellowcoin.settings.development
test:
	./manage.py test --settings=$(SETTINGS) 2>&1 | tee results.log
