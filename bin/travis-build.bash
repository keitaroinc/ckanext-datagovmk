#!/bin/bash
set -e

echo "This is travis-build.bash..."

echo "Installing the packages that CKAN requires..."
sudo apt-get update -qq
sudo apt-get install solr-jetty

echo "Installing CKAN and its Python dependencies..."
git clone https://github.com/ckan/ckan
cd ckan
export latest_ckan_release_branch=`git branch --all | grep remotes/origin/release-v | sort -r | sed 's/remotes\/origin\///g' | head -n 1`
echo "CKAN branch: $latest_ckan_release_branch"
git checkout $latest_ckan_release_branch
python setup.py develop
# Travis has an issue with older version of psycopg2 (2.4.5)
sed -i 's/psycopg2==2.4.5/psycopg2==2.7.3.2/' requirements.txt
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

# Install extensions
# ckanext-spatial and related
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-spatial.git@dgm-stable#egg=ckanext-spatial" && \
pip install --no-cache-dir -r "./ckanext-spatial/pip-requirements.txt" && \
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-report.git@dgm-stable#egg=ckanext-report" && \
# ckanext-qa and related
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-archiver.git@dgm-stable#egg=ckanext-archiver" && \
pip install --no-cache-dir -r "./ckanext-archiver/requirements.txt" && \
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-qa.git@dgm-stable#egg=ckanext-qa" && \
pip install --no-cache-dir -r "./ckanext-qa/requirements.txt" && \
# showcase
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-showcase.git@dgm-stable#egg=ckanext-showcase" && \
# harvest
pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest" && \
pip install --no-cache-dir -r "./ckanext-harvest/pip-requirements.txt" && \
# c3charts
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-c3charts.git@dgm-stable#egg=ckanext-c3charts" && \
# disqus
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-disqus.git@dgm-stable#egg=ckanext-disqus" && \
# dcat
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-dcat.git@dgm-stable#egg=ckanext-dcat" && \
pip install --no-cache-dir -r "./ckanext-dcat/requirements.txt" && \
# odata
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-odata@dgm-stable#egg=ckanext-odata" && \
# mk dcat-ap
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-mk_dcatap#egg=ckanext-mk_dcatap" && \
pip install --no-cache-dir -r "./ckanext-mk-dcatap/requirements.txt" && \
# envvars
pip install --no-cache-dir -e "git+https://github.com/okfn/ckanext-envvars.git#egg=ckanext-envvars" && \
pip install --no-cache-dir -r "./ckanext-envvars/dev-requirements.txt" && \
# pages
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-pages.git@dgm-stable#egg=ckanext-pages" && \
pip install --no-cache-dir -r "./ckanext-pages/dev-requirements.txt" && \
# scheming
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-scheming.git@dgm-stable#egg=ckanext-scheming" && \
pip install --no-cache-dir -r "./ckanext-scheming/requirements.txt" && \
# repeating
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-repeating.git#egg=ckanext-repeating" && \
# google analytics
pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-googleanalytics.git#egg=ckanext-googleanalytics" && \
pip install --no-cache-dir -r "./ckanext-googleanalytics/requirements.txt" && \
pip install --no-cache-dir oauth2client && \
# organogram
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-organogram.git@v0.2#egg=ckanext-organogram" && \
# validation
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-validation.git@dgm-stable#egg=ckanext-validation" && \
# skip scheming since we are using a fork
pip install --no-cache-dir $(cat ./ckanext-validation/requirements.txt | grep -ivE "ckanext-scheming") && \
# experience
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-experience.git#egg=ckanext-experience" && \
# requestdata
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-requestdata.git@dgm-stable#egg=ckanext-requestdata" && \
pip install --no-cache-dir -r "./ckanext-requestdata/requirements.txt" && \
# likes
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-likes.git#egg=ckanext-likes" && \
pip install --no-cache-dir -r "./ckanext-likes/requirements.txt" && \
# issues
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-issues.git@dgm-stable#egg=ckanext-issues" && \
# fluent
pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-fluent.git#egg=ckanext-fluent" && \
# dataexplorer
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-dataexplorer.git#egg=ckanext-dataexplorer" && \
pip install --no-cache-dir -r "./ckanext-dataexplorer/requirements.txt" && \
# datarequests
pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-datarequests.git@dgm-stable#egg=ckanext-datarequests"

echo "Installing ckanext-datagovmk and its requirements..."
python setup.py develop
pip install -r dev-requirements.txt

echo "Moving test.ini into a subdir..."
mkdir subdir
mv test.ini subdir

echo "travis-build.bash is done."