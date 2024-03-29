"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

import os
import sys
import subprocess
import psycopg2
import urllib.request
import urllib.error


ckan_ini = os.environ.get('CKAN_INI', '/srv/app/production.ini')

RETRY = 5

def check_db_connection(retry=None):

    if retry is None:
        retry = RETRY
    elif retry == 0:
        print ('[prerun] Giving up after 5 tries...')
        sys.exit(1)

    conn_str = os.environ.get('CKAN_SQLALCHEMY_URL', '')
    try:
        connection = psycopg2.connect(conn_str)

    except psycopg2.Error as e:
        print (str(e))
        print ('[prerun] Unable to connect to the database...try again in a while.')
        import time
        time.sleep(10)
        check_db_connection(retry = retry - 1)
    else:
        connection.close()

def check_solr_connection(retry=None):

    if retry is None:
        retry = RETRY
    elif retry == 0:
        print ('[prerun] Giving up after 5 tries...')
        sys.exit(1)

    url = os.environ.get('CKAN_SOLR_URL', '')
    search_url = '{url}/select/?q=*&wt=json'.format(url=url)

    try:
        connection = urllib.request.urlopen(search_url)
    except urllib.error.URLError as e:
        print (str(e))
        print ('[prerun] Unable to connect to solr...try again in a while.')
        import time
        time.sleep(10)
        check_solr_connection(retry = retry - 1)
    else:
        import re
        conn_info = connection.read()
        conn_info = re.sub(r'"zkConnected":true', '"zkConnected":True', conn_info)
        eval(conn_info)

def init_db():

    db_command = ['paster', '--plugin=ckan', 'db', 'init', '-c', ckan_ini]
    report_command = ['paster', '--plugin=ckanext-report', 'report', 'initdb', '-c', ckan_ini]
    archiver_command = ['paster', '--plugin=ckanext-archiver', 'archiver', 'init', '-c', ckan_ini]
    qa_command = ['paster', '--plugin=ckanext-qa', 'qa', 'init', '-c', ckan_ini]
    harvest_command = ['paster', '--plugin=ckanext-harvest', 'harvester', 'initdb', '-c', ckan_ini]
    analytics_command = ['paster', '--plugin=ckanext-googleanalytics', 'initdb', '-c', ckan_ini]
    # Disabled for restart. Enable if using on first run, to init the db
    # validation_command = ['paster', '--plugin=ckanext-validation', 'validation', 'init-db', '-c', ckan_ini]
    issues_command = ['paster', '--plugin=ckanext-issues', 'issues', 'init_db', '-c', ckan_ini]
    datagovmk_command = ['paster', '--plugin=ckanext-datagovmk', 'initdb', '-c', ckan_ini]

    print ('[prerun] Initializing or upgrading db - start')
    try:
        # run init scripts
        subprocess.check_output(db_command, stderr=subprocess.STDOUT)
        subprocess.check_output(report_command, stderr=subprocess.STDOUT)
        subprocess.check_output(archiver_command, stderr=subprocess.STDOUT)
        subprocess.check_output(qa_command, stderr=subprocess.STDOUT)
        subprocess.check_output(harvest_command, stderr=subprocess.STDOUT)
        subprocess.check_output(analytics_command, stderr=subprocess.STDOUT)
        # Disable on restart, enable on first run to init the db
        # subprocess.check_output(validation_command, stderr=subprocess.STDOUT)
        subprocess.check_output(issues_command, stderr=subprocess.STDOUT)
        subprocess.check_output(datagovmk_command, stderr=subprocess.STDOUT)

        print ('[prerun] Initializing or upgrading db - end')
    except subprocess.CalledProcessError as e:
        if 'OperationalError' in e.output:
            print (e.output)
            print ('[prerun] Database not ready, waiting a bit before exit...')
            import time
            time.sleep(5)
            sys.exit(1)
        else:
            print (e.output)
            raise e
    print ('[prerun] Initializing or upgrading db - finish')

def create_sysadmin():

    name = os.environ.get('CKAN_SYSADMIN_NAME')
    password = os.environ.get('CKAN_SYSADMIN_PASSWORD')
    email = os.environ.get('CKAN_SYSADMIN_EMAIL')

    if name and password and email:

        # Check if user exists
        command = ['paster', '--plugin=ckan', 'user', name, '-c', ckan_ini]

        out = subprocess.check_output(command)
        if 'User: \nNone\n' not in out:
            print ('[prerun] Sysadmin user exists, skipping creation')
            return

        # Create user
        command = ['paster', '--plugin=ckan', 'user', 'add',
                   name,
                   'password=' + password,
                   'email=' + email,
                   '-c', ckan_ini]

        subprocess.call(command)
        print ('[prerun] Created user {0}'.format(name))

        # Make it sysadmin
        command = ['paster', '--plugin=ckan', 'sysadmin', 'add',
                   name,
                   '-c', ckan_ini]

        subprocess.call(command)
        print ('[prerun] Made user {0} a sysadmin'.format(name))

def run_background_jobs():
    print ('[prerun] Starting background jobs - start')
    archiver_bulk_command = ['paster', '--plugin=ckan', 'jobs', 'worker', 'bulk', '-c', ckan_ini]
    archiver_priority_command = ['paster', '--plugin=ckan', 'jobs', 'worker', 'priority', '-c', ckan_ini]
    validator_default_command = ['paster', '--plugin=ckan', 'jobs', 'worker', 'default', '-c', ckan_ini]

    # run in background
    subprocess.Popen(archiver_bulk_command)
    subprocess.Popen(archiver_priority_command)
    subprocess.Popen(validator_default_command)
    print ('[prerun] Starting background jobs - finish')

if __name__ == '__main__':

    maintenance = os.environ.get('MAINTENANCE_MODE', '').lower() == 'true'

    if maintenance:
        print ('[prerun] Maintenance mode, skipping setup...')
    else:
        check_db_connection()
        check_solr_connection()
        init_db()
        create_sysadmin()
        run_background_jobs()
