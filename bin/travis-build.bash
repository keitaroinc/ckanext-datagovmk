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
# Travis has an issue with older version of psycopg2 (2.4.5)
sed -i 's/psycopg2==2.4.5/psycopg2==2.7.3.2/' requirements.txt
pip install -r requirements.txt
pip install -r dev-requirements.txt
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

# go out of ckanext-datagovmk extension
cd ..

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

echo "Installing ckanext-scheming and its requirements..."
git clone https://github.com/keitaroinc/ckanext-scheming.git
cd ckanext-scheming
git checkout dgm-stable
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-fluent and its requirements..."
git clone https://github.com/ckan/ckanext-fluent.git
cd ckanext-fluent
python setup.py develop
cd -

echo "Installing ckanext-harvest and its requirements..."
git clone https://github.com/ckan/ckanext-harvest.git
cd ckanext-harvest
python setup.py develop
pip install -r pip-requirements.txt
cd -

echo "Installing ckanext-mk_dcatap and its requirements..."
git clone https://github.com/keitaroinc/ckanext-mk_dcatap
cd ckanext-mk_dcatap
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-validation and its requirements..."
git clone https://github.com/keitaroinc/ckanext-validation.git
cd ckanext-validation
git checkout dgm-stable
python setup.py develop
pip install --no-cache-dir $(cat requirements.txt | grep -ivE "ckanext-scheming")
cd -

echo "Installing ckanext-repeating and its requirements..."
git clone https://github.com/keitaroinc/ckanext-repeating.git
cd ckanext-repeating
python setup.py develop
cd -

echo "Installing ckanext-spatial and its requirements..."
git clone https://github.com/keitaroinc/ckanext-spatial.git
cd ckanext-spatial
git checkout dgm-stable
python setup.py develop
pip install -r pip-requirements.txt
cd -

echo "Installing ckanext-report and its requirements..."
git clone https://github.com/keitaroinc/ckanext-report.git
cd ckanext-report
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-archiver and its requirements..."
git clone https://github.com/keitaroinc/ckanext-archiver.git
cd ckanext-archiver
git checkout dgm-stable
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-qa and its requirements..."
git clone https://github.com/keitaroinc/ckanext-qa.git
cd ckanext-qa
git checkout dgm-stable
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-showcase and its requirements..."
git clone https://github.com/keitaroinc/ckanext-showcase.git
cd ckanext-showcase
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-disqus and its requirements..."
git clone https://github.com/keitaroinc/ckanext-disqus.git
cd ckanext-disqus
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-odata and its requirements..."
git clone https://github.com/keitaroinc/ckanext-odata.git
cd ckanext-odata
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-envvars and its requirements..."
git clone https://github.com/okfn/ckanext-envvars.git
cd ckanext-envvars
python setup.py develop
pip install -r dev-requirements.txt
cd -

echo "Installing ckanext-pages and its requirements..."
git clone https://github.com/keitaroinc/ckanext-pages.git
cd ckanext-pages
git checkout dgm-stable
python setup.py develop
pip install -r dev-requirements.txt
cd -

echo "Installing ckanext-organogram and its requirements..."
git clone https://github.com/keitaroinc/ckanext-organogram.git
cd ckanext-organogram
python setup.py develop
cd -

echo "Installing ckanext-experience and its requirements..."
git clone https://github.com/keitaroinc/ckanext-experience.git
cd ckanext-experience
python setup.py develop
cd -

echo "Installing ckanext-requestdata and its requirements..."
git clone https://github.com/keitaroinc/ckanext-requestdata.git
cd ckanext-requestdata
git checkout dgm-stable
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-likes and its requirements..."
git clone https://github.com/keitaroinc/ckanext-likes.git
cd ckanext-likes
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-issues and its requirements..."
git clone https://github.com/keitaroinc/ckanext-issues.git
cd ckanext-issues
git checkout dgm-stable
python setup.py develop
cd -

echo "Installing ckanext-dataexplorer and its requirements..."
git clone https://github.com/keitaroinc/ckanext-dataexplorer.git
cd ckanext-dataexplorer
python setup.py develop
pip install -r requirements.txt
cd -

echo "Installing ckanext-datarequests and its requirements..."
git clone https://github.com/keitaroinc/ckanext-datarequests.git
cd ckanext-datarequests
git checkout dgm-stable
python setup.py develop
cd -

# return to ckanext-datagovmk extension
cd ckanext-datagovmk

echo "travis-build.bash is done."