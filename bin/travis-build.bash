#!/bin/bash
set -e

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
echo "CKAN branch: ckan-2.8.1"
git checkout ckan-2.8.1
python setup.py develop
pip install -r requirements.txt --allow-all-external
pip install -r dev-requirements.txt --allow-all-external
cd -

echo "Creating the PostgreSQL user and database..."
sudo -u postgres psql -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
sudo -u postgres psql -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "SOLR config..."
# Solr is multicore for tests on ckan master, but it's easier to run tests on
# Travis single-core. See https://github.com/ckan/ckan/issues/2972
sed -i -e 's/solr_url.*/solr_url = http:\/\/127.0.0.1:8983\/solr/' ckan/test-core.ini

echo "Initialising the database..."
cd ckan
paster db init -c test-core.ini
cd -

echo "Installing ckanext-datagovmk and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt

echo "Installing ckanext-googleanalytics and its requirements..."
git clone https://github.com/ckan/ckanext-googleanalytics
cd ckanext-googleanalytics
python setup.py develop
pip install -r requirements.txt
pip install oauth2client
cd -

echo "Installing ckanext-c3charts and its requirements..."
git clone https://github.com/keitaroinc/ckanext-c3charts.git
cd ckanext-c3charts
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-dcat and its requirements..."
git clone https://github.com/keitaroinc/ckanext-dcat.git
cd ckanext-dcat
git checkout dgm-stable
python setup.py develop
pip install -r requirements.txt
cd -

echo "travis-build.bash is done."