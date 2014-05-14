#!/bin/bash

# syntax: source $0 ( HTTP | VIRTUALENV | ENQ | DEQ ) ( staging | production | development )

# to re-link settings module, change environment variable DJANGO_SETTINGS_MODULE in
#	1.) ~/.bashrc
#	2.) /etc/apache2/apache2.conf
# to appropriate settings after installation

# may need to dropdb, createdb for postgres if models have changed (to wipe table metadata)

MODE="$1"
MODULE="$2"

case $MODE in
	"HTTP" | "VIRTUALENV" | "ENQ" | "DEQ")
		echo "setting up this node in $MODE mode"
		;;
	*)
		echo "invalid settings -- MODE oneof HTTP | VIRTUALENV | ENQ"
		exit 0
		;;
esac

case $MODULE in
	"staging" | "production" | "development")
		echo "setting up this node in $MODULE environment"
		;;
	*)
		echo "invalid settings -- MODULE oneof staging | production | development"
		exit 0
		;;
esac

SETTINGS="yellowcoin.settings.$MODULE"

case $MODE in
	"VIRTUALENV")
		;;
	*)
		# set the default settings for django -- change manually to production.py to commit to live
		echo "export DJANGO_SETTINGS_MODULE=$SETTINGS" >> ~/.bashrc
		source ~/.bashrc
		;;
esac

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

cd yellowcoin

sudo chmod -R ugo+rwx /var/www/yellowcoin/cache/
sudo chmod -R ugo+rwx /var/www/yellowcoin/logs/

sudo chmod ugo+s /var/www/yellowcoin/cache/
sudo chmod ugo+s /var/www/yellowcoin/logs/

case $MODE in
	"VIRTUALENV")
		# start virtualenv
		. ../bin/activate

		# install supplementary apps
		# cf. http://bit.ly/RMBJhx to why ez_setup needs to be installed separately
		pip install ez_setup
		pip install -r references/requirements.txt
		;;
	*)
		sudo pip install ez_setup
		sudo pip install -r references/requirements.txt
		;;
esac

# ensure everything is working correctly in the almost-live stage
case $MODULE in
	"development")
		# python /var/www/yellowcoin/manage.py test 2> check.log
		;;
	*)
		;;
esac

# logging for task.py production
case $MODULE in
	"development")
		# mv /var/www/yellowcoin/logs/audit.log /var/www/yellowcoin/logs/audit.check.log
		# mv /var/www/yellowcoin/logs/daemons.log /var/www/yellowcoin/logs/daemons.check.log
		touch /var/www/yellowcoin/logs/audit.log
		touch /var/www/yellowcoin/logs/daemons.log
		;;
	*)
		;;
esac

python /var/www/yellowcoin/manage.py syncdb

# setup Apache
case $MODE in
	"HTTP")
		sudo rm /etc/apache2/sites-enabled/*
		sudo rm /etc/apache2/sites-available/*

		sudo cp references/yellowcoin.conf /etc/apache2/sites-enabled/
		sudo ln -s /etc/apache2/sites-enabled/yellowcoin.conf /etc/apache2/sites-available/

		sudo tee -a /etc/apache2/apache2.conf < references/wsgi_setup.txt

		# set the environment variable in the server instance
		echo "SetEnv DJANGO_SETTINGS_MODULE $SETTINGS" | sudo tee -a /etc/apache2/apache2.conf

		sudo chown -R www-data:www-data /var/www/yellowcoin/
		;;
	"ENQ")
		sudo sed -ie '$d' /etc/rc.local
		echo "sudo -u yc-enq python /var/www/yellowcoin/manage.py cycle --settings=$SETTINGS &" | sudo tee -a /etc/rc.local
		echo "exit 0" | sudo tee -a /etc/rc.local

		sudo useradd --system yc-enq
		sudo chown -R yc-enq:yc-enq /var/www/yellowcoin/
		;;
	"DEQ")
		# cf. http://bit.ly/1gwBT22
		sudo cp references/celeryd.sh /etc/init.d/celeryd
		sudo cp references/celeryd.conf /etc/default/celeryd
		echo "export DJANGO_SETTINGS_MODULE=$SETTINGS" | sudo tee -a /etc/default/celeryd
		sudo chmod +x /etc/init.d/celeryd
		sudo chmod 400 /etc/default/celeryd

		sudo useradd --system yc-deq
		sudo chown -R yc-deq:yc-deq /var/www/yellowcoin/

		sudo sed -ie '$d' /etc/rc.local
		echo "sudo /etc/init.d/celeryd start" | sudo tee -a /etc/rc.local
		echo "exit 0" | sudo tee -a /etc/rc.local

		# sudo update-rc.d celeryd defaults
		;;
	*)
		;;
esac

sudo reboot
