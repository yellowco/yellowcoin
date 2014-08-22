SETTINGS=yellowcoin.settings.development
test:
	./manage.py test --settings=$(SETTINGS) 2> out.log

