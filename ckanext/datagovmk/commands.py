# -*- coding: utf-8 -*-

from logging import getLogger
from datetime import timedelta, datetime
from dateutil import parser

from ckan.lib.cli import CkanCommand
from ckan.plugins import toolkit
import ckan.lib.helpers as h
import ckan.lib.mailer as ckan_mailer
from ckan.lib import base
from ckan.common import config
import os
import io
import inspect
from ckanext.datagovmk.model.user_authority \
    import setup as setup_user_authority_table
from ckanext.datagovmk.model.user_authority_dataset \
    import setup as setup_user_authority_dataset_table

log = getLogger('ckanext.datagovmk')

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
        
        frequency = frequency.split('/')[-1]

        if frequency in IGNORE_PERIODICITY:
            return  # not scheduled by choice
        
        periodicity = PERIODICITY.get(frequency.upper())
        if not periodicity:
            log.warning('Dataset %s has periodicity %s which we do not handle', dataset['id'], frequency)
            return  # we don't know how to handle this periodicity


        last_modified = self._get_last_modified(dataset)
        if not last_modified:
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

            return min(last_modified)
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
    ''' Initialize UserAuthority tables. '''

    summary = __doc__.split('\n')[0]
    usage = __doc__
    max_args = 0
    min_args = 0

    def command(self):
        self._load_config()
        
        setup_user_authority_table()
        setup_user_authority_dataset_table()

        log.info('User authorities tables initialized')