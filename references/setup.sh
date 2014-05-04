#!/bin/bash

MODE="$1"

case $MODE in
	"HTTP" | "VIRTUALENV" | "ENQ")
		echo "setting up this node in $MODE mode"
		;;
	*)
		echo "invalid settings -- oneof HTTP | VIRTUALENV | ENQ"
		exit 0
		;;
esac

# TODO -- set up bitcoin client

# may need to dropdb, createdb for postgres if models have changed (to wipe table metadata)

# enable multiverse
sudo sed -i "/^# deb.*multiverse/ s/^# //" /etc/apt/sources.list
sudo aptitude update
sudo aptitude -y upgrade

# install Apache, mod_wsgi, PostgreSQL bindings, and geoip packages
case $MODE in
	"HTTP")
		sudo aptitude -y install apache2 libapache2-mod-wsgi
		;;
	*)
		;;
esac

sudo aptitude -y install python-psycopg2 geoip-database-contrib postgresql-client
sudo aptitude -y install git python-pip libpq-dev python-dev

case $MODE in
	"HTTP")
		git clone --recursive https://github.com/kevmo314/yellowcoin.git
		sudo ln -s ~/yellowcoin /var/www/yellowcoin
		;;
	"VIRTUALENV")
		# run the app in a virtual environment
		pip install STAGING

		STAGING yc && sudo ln -s ~/yc /var/www/yc && cd yc

		# checkout all user-side apps
		git clone --recursive https://github.com/kevmo314/yellowcoin.git
		;;
	*)
		git clone --recursive https://github.com/kevmo314/yellowcoin.git
		;;
esac

cd yellowcoin

case $MODE in
	"VIRTUALENV")
		# start STAGING
		. ../bin/activate

		# install supplementary apps
		# cf. http://bit.ly/RMBJhx to why ez_setup needs to be installed separately
		pip install ez_setup
		pip install -r requirements.txt
		;;
	*)
		sudo pip install ez_setup
		sudo pip install -r requirements.txt
		;;
esac

# ensure everything is working correctly
./manage.py test --settings=yellowcoin.settings.staging 2> check.log

case $MODE in
	"VIRTUALENV")
		;;
	*)
		# set the default settings for django to be staging.py -- change manually to production.py to commit to live
		echo 'export DJANGO_SETTINGS_MODULE=yellowcoin.settings.staging' >> ~/.bashrc
		source ~/.bashrc
		;;
esac

# setup Apache
case $MODE in
	"HTTP")
		sudo rm /etc/apache2/sites-enabled/*
		sudo rm /etc/apache2/sites-available/*

		sudo cp references/yellowcoin.conf /etc/apache2/sites-enabled/
		sudo ln -s /etc/apache2/sites-enabled/yellowcoin.conf /etc/apache2/sites-available/

		sudo tee -a /etc/apache2/apache2.conf < references/wsgipythonpath.txt
		sudo /etc/init.d/apache2 restart

		./manage.py syncdb
		;;
	"ENQ")
		sudo sed -ie '$d' /etc/rc.local
		echo 'python /var/www/yellowcoin/manage.py cycle --settings=yellowcoin.settings.staging' | sudo tee -a /etc/rc.local
		echo 'python /var/www/yellowcoin/manage.py execute --settings=yellowcoin.settings.staging' | sudo tee -a /etc/rc.local
		echo 'exit 0' | sudo tee -a /etc/rc.local
		sudo sudo /etc/init.d/rc.local start
		./manage.py cycle
		;;
	*)
		;;
esac
