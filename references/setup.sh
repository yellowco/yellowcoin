#!/bin/bash

# TODO -- set up bitcoin client

# may need to dropdb, createdb for postgres if models have changed (to wipe table metadata)

# enable multiverse
sudo sed -i "/^# deb.*multiverse/ s/^# //" /etc/apt/sources.list
sudo aptitude update
sudo aptitude -y upgrade

# install Apache, mod_wsgi, PostgreSQL bindings, and geoip packages
sudo aptitude -y install apache2 libapache2-mod-wsgi python-psycopg2 geoip-database-contrib postgresql-client
sudo aptitude -y install git python-pip libpq-dev python-dev

if [ "$1" = "VIRTUALENV" ];
then
	# run the app in a virtual environment
	pip install STAGING

	STAGING yc && sudo ln -s ~/yc /var/www/yc && cd yc

	# checkout all user-side apps
	git clone --recursive https://github.com/kevmo314/yellowcoin.git
else
	git clone --recursive https://github.com/kevmo314/yellowcoin.git
	sudo ln -s ~/yellowcoin /var/www/yellowcoin
fi

cd yellowcoin

if [ "$1" = "VIRTUALENV" ];
then
	# start STAGING
	. ../bin/activate

	# install supplementary apps
	# cf. http://bit.ly/RMBJhx to why ez_setup needs to be installed separately
	pip install ez_setup
	pip install -r requirements.txt
else
	sudo pip install ez_setup
	sudo pip install -r requirements.txt
fi

# ensure everything is working correctly
./manage.py test --settings=yellowcoin.settings.staging 2> check.log

# setup Apache
if [ "$1" != "VIRTUALENV" ];
then
	sudo rm /etc/apache2/sites-enabled/*
	sudo rm /etc/apache2/sites-available/*

	sudo cp references/yellowcoin.conf /etc/apache2/sites-enabled/
	sudo ln -s /etc/apache2/sites-enabled/yellowcoin.conf /etc/apache2/sites-available/

	sudo tee -a /etc/apache2/apache2.conf < references/wsgipythonpath.txt
	sudo /etc/init.d/apache2 restart

	./manage.py syncdb --settings=yellowcoin.settings.staging

	# set the default settings for django to be staging.py -- change manually to production.py to commit to live
	echo 'export DJANGO_SETTINGS_MODULE=yellowcoin.settings.staging' >> ~/.bashrc
	source ~/.bashrc
fi
