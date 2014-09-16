SETTINGS?=yellowcoin.settings.development
all:
	./manage.py test --settings=$(SETTINGS) 2>&1 | tee results.log
