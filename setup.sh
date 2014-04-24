# install Apache, mod_wsgi, PostgreSQL bindings, and geoip packages
sudo aptitude install apache2 libapache2-mod-wsgi python-psycopg2 geoip-database-contrib postgresql-client
sudo aptitude install libpq-dev python-dev

# run the app in a virtual environment
pip install virtualenv

virtualenv yc && sudo ln -s ~/yc /var/www/ && cd yc

# checkout all user-side apps
git clone --recursive https://github.com/kevmo314/yellowcoin.git && cd yellowcoin

# start virtualenv
. ../bin/activate

# install supplementary apps
# cf. http://bit.ly/RMBJhx to why ez_setup needs to be installed separately
pip install ez_setup
pip install -r requirements.txt

# ensure everything is working correctly
./manage.py test
