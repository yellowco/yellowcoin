#!/bin/bash

MODE="$1"
MODULE="$2"

case $MODE in
	"HTTP" | "VIRTUALENV" | "ENQ")
		echo "setting up this node in $MODE mode"
		;;
	*)
		echo "invalid settings -- MODE oneof HTTP | VIRTUALENV | ENQ"
		exit 0
		;;
esac

case $MODULE in
	"staging" | "alpha" | "beta" | "production" | "development")
		echo "setting up this node in $MODULE environment"
		;;
	*)
		echo "invalid settings -- MODULE oneof staging | alpha | beta | production | development"
		exit 0
		;;
esac

SETTINGS="yellowcoin.settings.$MODULE"

case $MODE in
	"VIRTUALENV")
		;;
	*)
		# set the default settings for django to be staging.py -- change manually to production.py to commit to live
		echo "export DJANGO_SETTINGS_MODULE=$SETTINGS" >> ~/.bashrc
		source ~/.bashrc
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
		pip install virtualenv

		virtualenv yc && sudo ln -s ~/yc /var/www/yc && cd yc

		# checkout all user-side apps
		git clone --recursive https://github.com/kevmo314/yellowcoin.git
		;;
	*)
		git clone --recursive https://github.com/kevmo314/yellowcoin.git
		sudo mkdir /var/www
		sudo ln -s ~/yellowcoin /var/www/yellowcoin
		;;
esac

# logging for tasks.py
sudo touch /var/www/yellowcoin/logs/audit.log
sudo chmod ugo+rw /var/www/yellowcoin/logs/audit.log

cd yellowcoin

case $MODE in
	"VIRTUALENV")
		# start virtualenv
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

# ensure everything is working correctly in the almost-live stage
case $MODULE in
	"staging")
		./manage.py test --settings=yellowcoin.settings.staging 2> check.log
		;;
	"development")
		./manage.py test --settings=yellowcoin.settings.development 2> check.log
		;;
	*)
		;;
esac

./manage.py syncdb

# setup Apache
case $MODE in
	"HTTP")
		sudo rm /etc/apache2/sites-enabled/*
		sudo rm /etc/apache2/sites-available/*

		sudo cp references/yellowcoin.conf /etc/apache2/sites-enabled/
		sudo ln -s /etc/apache2/sites-enabled/yellowcoin.conf /etc/apache2/sites-available/

		# set the environment variable in the server instance
		echo "SetEnv DJANGO_SETTINGS_MODULE $SETTINGS" >> references/set_env.txt

		sudo tee -a /etc/apache2/apache2.conf < references/wsgi_setup.txt
		sudo tee -a /etc/apache2/apache2.conf < references/set_env.txt

		rm references/set_env.txt

		sudo /etc/init.d/apache2 restart
		;;
	"ENQ")
		sudo sed -ie '$d' /etc/rc.local
		echo 'python /var/www/yellowcoin/manage.py cycle' | sudo tee -a /etc/rc.local
		echo 'python /var/www/yellowcoin/manage.py execute' | sudo tee -a /etc/rc.local
		echo 'exit 0' | sudo tee -a /etc/rc.local
		sudo /etc/init.d/rc.local start
		;;
	*)
		;;
esac
