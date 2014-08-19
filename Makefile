SETTINGS=yellowcoin.settings.development
all:
	./manage.py test --settings=$(SETTINGS) 2> out.log

