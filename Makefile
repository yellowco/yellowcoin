SETTINGS?=yellowcoin.settings.development
all:
	./manage.py test --settings=$(SETTINGS) | tee results.log
