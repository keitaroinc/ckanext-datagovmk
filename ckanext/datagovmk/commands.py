# -*- coding: utf-8 -*-

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
import io
import inspect
import json

from logging import getLogger
from datetime import timedelta, datetime
from dateutil import parser

from ckan.lib.cli import CkanCommand
from ckan.plugins import toolkit
import ckan.lib.helpers as h
import ckan.lib.mailer as ckan_mailer
from ckan.lib import base
from ckan.common import config

from ckanext.datagovmk.model.user_authority \
    import setup as setup_user_authority_table
from ckanext.datagovmk.model.user_authority_dataset \
    import setup as setup_user_authority_dataset_table
from ckanext.datagovmk.model.most_active_organizations \
    import setup as setup_most_active_organizations_table
from ckanext.datagovmk.model.sort_organizations \
    import setup as setup_sort_organizations_table
from ckanext.datagovmk.model.sort_groups \
    import setup as setup_sort_groups_table
from ckanext.datagovmk.model.most_active_organizations import MostActiveOrganizations
from ckanext.datagovmk.model.sort_organizations import SortOrganizations as SortOrganizationsModel
from ckanext.datagovmk.model.sort_groups import SortGroups as SortGroupsModel
from ckanext.datagovmk.helpers import get_most_active_organizations
from ckan.model.meta import Session
from ckan.controllers.admin import get_sysadmins
from ckan.logic.action.get import organization_list as ckan_organization_list
from ckan.logic.action.get import group_list as _group_list


log = getLogger('ckanext.datagovmk')
ValidationError = toolkit.ValidationError

BULK_SIZE = 5


PERIODICITY = {
    'ANNUAL': timedelta(days=365),
    'ANNUAL_2': timedelta(days=365/2),
    'ANNUAL_3': timedelta(days=365/3),
    'BIENNIAL': timedelta(days=2*365),
    'BIMONTHLY': timedelta(days=2*30),
    'BIWEEKLY': timedelta(weeks=2),
    'CONT': timedelta(minutes=1),
    'DAILY': timedelta(days=1),
    'DAILY_2': timedelta(days=2),
    'MONTHLY': timedelta(days=4*30),
    'MONTHLY_2': timedelta(days=15),
    'MONTHLY_3': timedelta(days=10),
    'QUARTERLY': timedelta(days=3*30),
    'TRIENNIAL': timedelta(days=3*365),
    'UPDATE_CONT': timedelta(minutes=1),
    'WEEKLY': timedelta(weeks=1),
    'WEEKLY_2': timedelta(weeks=0.5),
    'WEEKLY_3': timedelta(weeks=3),
}

IGNORE_PERIODICITY = {'IRREG', 'OTHER', 'UNKNOWN', 'NEVER'}


class CheckOutdatedDatasets(CkanCommand):
    ''' Check update frequency for datasets. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()
        self._processl_all_datasets(self._check_dataset_if_outdated)

    def _processl_all_datasets(self, process_dataset):
        context = {'ignore_auth': True}
        page = 0

        while True:
            query = {
                'include_private': True,
                'rows': BULK_SIZE,
                'start': page*BULK_SIZE
            }
            datasets = toolkit.get_action('package_search')(context, query)

            for result in datasets['results']:
                dataset = toolkit.get_action('package_show')(context, {'id': result['id']})
                try:
                    process_dataset(dataset)
                except Exception as e:
                    log.debug('An error has occured while processing dataset. Error: %s', e)
            page += 1
            if page*BULK_SIZE >= datasets['count']:
                break


    def _check_dataset_if_outdated(self, dataset):

        frequency = dataset.get('frequency')
        if not frequency:
            return  # ignore, not scheduled for periodic updates
        print("Frequency is: " + frequency)

        frequency = frequency.split('/')[-1]
        if frequency in IGNORE_PERIODICITY:
            print("Does it return here?! Frequency in ignore_periodicity")
            return  # not scheduled by choice
        periodicity = PERIODICITY.get(frequency.upper())
        if not periodicity:
            print("Not periodicity return!")
            log.warning('Dataset %s has periodicity %s which we do not handle', dataset['id'], frequency)
            return  # we don't know how to handle this periodicity


        last_modified = self._get_last_modified(dataset)
        if not last_modified:
            print("not last modified, return!")
            return  # ignore this one

        now = datetime.now()

        diff = now - last_modified
        if diff >= periodicity:
            log.debug('Dataset %s needs to be updated.', dataset['id'])
            self.notify_dataset_outdated(dataset, last_modified)
            log.info('Notifications for dataset update has beed sent. Dataset: %s', dataset['id'])


    def _get_last_modified(self, dataset):
        resources = dataset.get('resources')
        if resources:
            last_modified = []
            for resource in resources:
                lm = resource.get('last_modified') or resource.get('created')
                if lm:
                    last_modified.append(parser.parse(lm))

            return max(last_modified)
        return None

    def _get_dataset_users(self, dataset):
        users = []
        if dataset.get('maintainer_email'):
            maintainer = {'email': dataset['maintainer_email']}
            maintainer['username'] = dataset.get('maintainer') or dataset['maintainer_email'].split('@')[0]

            users.append(maintainer)

        if dataset.get('creator_user_id'):
            try:
                creator = toolkit.get_action('user_show')({'ignore_auth' :True}, {'id': dataset['creator_user_id']})
                users.append({
                    'email': creator['email'],
                    'username': creator.get('fullname') or creator.get('name')
                })

            except toolkit.NotFound:
                pass

        return users

    def notify_dataset_outdated(self, dataset, last_modified):
        """ This function will notify if a dataset is outdated
        :param dataset: the dataset that needs to be checked if it is outdated
        :type dataset: dict
        :param last_modified: date of the last time the dataset was modified
        :type last_modified: str
        """
        dataset_url = h.url_for(controller='package', action='read', id=dataset['name'], qualified=True)
        dataset_update_url = h.url_for(controller='package', action='edit', id=dataset['name'], qualified=True)
        dataset_title = dataset.get('title') or dataset.get('name')

        dataset_users = self._get_dataset_users(dataset)

        for user in dataset_users:
            try:
                self._send_notification(dataset_url, dataset_update_url, dataset_title, user)
            except Exception as e:
                log.error('Failed to send email notification for dataset %s: %s', dataset['id'], e)

    def _send_notification(self, dataset_url, dataset_update_url, dataset_title, user):
        subject = u'CKAN: Потсетување за ажурирање на податочниот сет „{title}“ | '\
                  u'Kujtesë për përditësimin e të dhënave "{title}" | '\
                  u'Reminder to update dataset "{title}"'.format(title=dataset_title)
        try:
            body =_load_resource_from_path('ckanext.datagovmk:templates/datagovmk/outdated_dataset_email.html').format(**{
                'username': user['username'],
                'dataset_url': dataset_url,
                'dataset_title': dataset_title,
                'dataset_update_url': dataset_update_url,
                'site_title': config.get('ckan.site_title', 'CKAN')
            })

            ckan_mailer.mail_recipient(user['email'], user['email'], subject,
                                       body, headers={
                                           'Content-Type': 'text/html; charset=UTF-8',
                                       })
        except ckan_mailer.MailerException as e:
            log.error('Failed to send notification message for updating the obsolete dataset %s: %s', dataset_title, e)


def _load_resource_from_path(url):
    """
    Given a path like "ckanext.mk_dcatap:resource.json"
    find the second part relative to the import path of the first
    """

    module, file_name = url.split(':', 1)
    try:
        # __import__ has an odd signature
        m = __import__(module, fromlist=[''])
    except ImportError:
        raise
    p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
    with io.open(p, mode='r', encoding='utf-8') as resource_file:
        return resource_file.read()


class InitDB(CkanCommand):
    ''' Initialize datagovmk DB tables. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()

        setup_user_authority_table()
        setup_user_authority_dataset_table()
        setup_most_active_organizations_table()
        setup_sort_organizations_table()
        setup_sort_groups_table()

        log.info('datagovmk DB tables initialized')


class SortOrganizations(CkanCommand):
    ''' Sorts organizations. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0
    
    def command(self):
            self._load_config()
            create_sort_organizations()

def create_sort_organizations():
    
    sysadmin = get_sysadmins()[0].name
    context = {
            'user': sysadmin,
            'ignore_auth': True
    }
    orgs = ckan_organization_list(context, {})
    sort_org = []

    for org_name in orgs:
        org = toolkit.get_action('organization_show')({'user': None}, {
            'id': org_name,
            'include_datasets': True,
            'include_dataset_count': False,
            'include_extras': True,
            'include_users': False,
            'include_groups': False,
            'include_tags': False,
            'include_followers': False
        })
        if org.get('state') == 'active':
            sort_org = {
                'org_id': org.get('id', ''),
                'title_mk': org.get('title_translated', {}).get('mk', ''),
                'title_en': org.get('title_translated', {}).get('en', ''),
                'title_sq': org.get('title_translated', {}).get('sq', '')
            }
        
            so = SortOrganizationsModel(**sort_org)
            so.save()

    return

class SortGroups(CkanCommand):
    ''' Sorts groups. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0
    
    def command(self):
            self._load_config()
            create_sort_groups()

def create_sort_groups():
    
    sysadmin = get_sysadmins()[0].name
    context = {
            'user': sysadmin,
            'ignore_auth': True
    }
    groups = _group_list(context, {})

    for group_name in groups:
        gr = toolkit.get_action('group_show')({'user': None}, {
            'id': group_name,
            'include_datasets': True,
            'include_dataset_count': False,
            'include_extras': True,
            'include_users': False,
            'include_groups': False,
            'include_tags': False,
            'include_followers': False
        })
        if gr.get('state') == 'active':
            sort_gr = {
                'group_id': gr.get('id', ''),
                'title_mk': gr.get('title_translated', {}).get('mk', ''),
                'title_en': gr.get('title_translated', {}).get('en', ''),
                'title_sq': gr.get('title_translated', {}).get('sq', '')
            }
        
            sg = SortGroupsModel(**sort_gr)
            sg.save()

    return

class FetchMostActiveOrganizations(CkanCommand):
    ''' Fetches most active organizations. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()
        fetch_most_active_orgs()


def fetch_most_active_orgs():
    orgs = toolkit.get_action('organization_list')({}, {})
    last_updated_orgs = []

    for org_name in orgs:
        org = toolkit.get_action('organization_show')({'user': None}, {
            'id': org_name,
            'include_datasets': True,
            'include_dataset_count': False,
            'include_extras': True,
            'include_users': False,
            'include_groups': False,
            'include_tags': False,
            'include_followers': False,
        })

        last_updated_datasets = []

        for dataset in org.get('packages'):
            dataset_full = toolkit.get_action('package_show')({}, {
                'id': dataset.get('id'),
            })
            last_modified_resource = ''

            for resource in dataset_full.get('resources'):
                field = 'last_modified'
                if resource.get('last_modified') is None:
                    field = 'created'

                if resource.get(field) > last_modified_resource:
                    last_modified_resource = resource.get(field)

            last_updated_datasets.append(last_modified_resource)
        last_updated_datasets = sorted(last_updated_datasets, reverse=True)

        if last_updated_datasets:
            last_modified_dataset = last_updated_datasets[0]
            last_updated_orgs.append({
                'org': org, 'last_modified': last_modified_dataset
            })

    sorted_orgs = sorted(
        last_updated_orgs,
        key=lambda k: k['last_modified'],
        reverse=True
    )

    orgs = map(lambda x: x.get('org'), sorted_orgs)

    Session.query(MostActiveOrganizations).delete()

    s = Session()
    objects = []

    for org in orgs:
        data = {
            'org_id': org.get('id'),
            'org_name': org.get('name'),
            'org_display_name': json.dumps(org.get('title_translated', None)),
        }
        objects.append(MostActiveOrganizations(**data))

    try:
        s.bulk_save_objects(objects)
        s.commit()
    except:
        s.rollback()
        raise
    finally:
        s.close()

    log.info('Successfully cached most active organizations.')


