#!/bin/bash

# install Apache, mod_wsgi, PostgreSQL bindings, and geoip packages
sudo aptitude install apache2 libapache2-mod-wsgi python-psycopg2 geoip-database-contrib postgresql-client
sudo aptitude install libpq-dev python-dev

if [ '$1'='VIRTUALENV' ];
then
	# run the app in a virtual environment
	pip install virtualenv

	virtualenv yc && sudo ln -s ~/yc /var/www/yc && cd yc

	# checkout all user-side apps
	git clone --recursive https://github.com/kevmo314/yellowcoin.git
else
	git clone --recursive https://github.com/kevmo314/yellowcoin.git

	# production server -- only site would be YC
	sudo rm -rf /var/www
	sudo ln -s ~/yellowcoin /var/www
fi

cd yellowcoin

if [ '$1'='VIRTUALENV' ];
then
	# start virtualenv
	. ../bin/activate
fi

# install supplementary apps
# cf. http://bit.ly/RMBJhx to why ez_setup needs to be installed separately
pip install ez_setup
pip install -r requirements.txt

# ensure everything is working correctly
./manage.py test
