# install Apache, mod_wsgi, PostgreSQL bindings, and geoip packages
aptitude install apache2 libapache2-mod-wsgi python-psycopg2 geoip-database-contrib

# run the app in a virtual environment
pip install virtualenv

virtualenv yc && sudo ln -s ~/yc ~/var/www/yc && cd yc

# checkout all user-side apps
git clone https://github.com/kevmo314/yellowcoin.git && cd yellowcoin
rmdir django_routing_numbers && git clone https://github.com/kevmo314/django_routing_numbers.git

# start virtualenv
. ../bin/activate

# install supplementary apps
pip install ez_setup
pip install -r requirements.txt

# ensure everything is working correctly
./manage.py test
