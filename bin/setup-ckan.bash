#!/bin/bash
set -e

echo "This is setup-ckan.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install xmlsec1 libxmlsec1-dev

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
git checkout 2.9
pip install -r requirement-setuptools.txt
python setup.py develop
pip install -r requirements.txt
pip install -r dev-requirements.txt
pip install pytest-ckan
cd -

echo "Creating the PostgreSQL user and database..."
psql -h localhost -U postgres -c "CREATE USER ckan_default WITH PASSWORD 'pass';"
psql -h localhost -U postgres -c 'CREATE DATABASE ckan_test WITH OWNER ckan_default;'

echo "Initialising the database..."
cd ckan
ckan -c test-core.ini db init
cd -

echo "Installing ckanext-datagovmk dependencies..."
echo "Installing ckanext-scheming"
pip install -e git+https://github.com/keitaroinc/ckanext-scheming.git@dgm-ckan2.9#egg=ckanext-scheming


echo "Installing ckanext-c3charts"
pip install -e git+https://github.com/keitaroinc/ckanext-c3charts.git@master#egg=ckanext-c3charts

echo "Installing ckanext-fluent"
pip install -e git+https://github.com/keitaroinc/ckanext-fluent.git@dgm-ckan2.9#egg=ckanext-fluent
pip install -r https://raw.githubusercontent.com/keitaroinc/ckanext-fluent/dgm-ckan2.9/requirements.txt

echo "Installing ckanext-mk_dcatap"
pip install -e git+https://github.com/keitaroinc/ckanext-mk_dcatap.git@dgm-ckan2.9#egg=ckanext-mk_dcatap

echo "Installing ckanext-validation"
pip install -e git+https://github.com/keitaroinc/ckanext-validation.git@dgm-ckan2.9#egg=ckanext-validation
pip install ckantoolkit>=0.0.3
pip install goodtables==1.5.1

echo "Installing ckanext-pages"
pip install -e git+https://github.com/keitaroinc/ckanext-pages.git@dgm-ckan2.9#egg=ckanext-pages
pip install -r https://raw.githubusercontent.com/keitaroinc/ckanext-pages/dgm-ckan2.9/requirements.txt

echo "Installing ckanext-repeating"
pip install -e git+https://github.com/keitaroinc/ckanext-repeating.git@dgm-ckan2.9#egg=ckanext-repeating

echo "Installing ckanext-datagovmk and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "setup-ckan.bash is done."