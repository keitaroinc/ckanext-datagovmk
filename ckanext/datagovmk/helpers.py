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

"""datagovmk custom helpers.
"""
import os
import json
import ckan.authz as authz

from ckan.plugins import toolkit
from ckan.lib import search, i18n
from datetime import datetime
from ckan.common import config
from ckanext.datagovmk.model.stats import (get_stats_for_package,
                                           get_stats_for_resource,
                                           get_total_package_downloads)

from logging import getLogger
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckan.lib import helpers as core_helpers
from ckanext.datagovmk.model.most_active_organizations import MostActiveOrganizations


log = getLogger(__name__)

def _get_action(action, context_dict, data_dict):
    return toolkit.get_action(action)(context_dict, data_dict)

def get_recently_updated_datasets(limit=5):
    '''
     Returns recent created or updated datasets.

    :param limit: Limit of the datasets to be returned. Default is 5.
    :type limit: integer

    :returns: a list of recently created or updated datasets
    :rtype: list

    '''
    try:
        pkg_search_results = toolkit.get_action('package_search')(data_dict={
            'sort': 'metadata_modified desc',
            'rows': limit,
        })['results']

    except (toolkit.ValidationError, search.SearchError):
        return []
    else:
        pkgs = []
        for pkg in pkg_search_results:
            package = toolkit.get_action('package_show')(
                data_dict={'id': pkg['id']})
            modified = datetime.strptime(
                package['metadata_modified'].split('T')[0], '%Y-%m-%d')
            package['days_ago_modified'] = ((datetime.now() - modified).days)
            pkgs.append(package)
        return pkgs

def get_most_active_organizations(limit=5):
    '''
    Returns most active organizations based on when new resource has been
    added to a dataset, or when an existing resource has been updated (new
    file has been added).

    :param limit: Number of organizations to be returned. Default is 5.
    :type limit: integer

    :returns: a list of the most active organizations.
    :rtype: list

    '''
    orgs = MostActiveOrganizations.get_all(limit=limit)

    return orgs


def get_related_datasets(id, limit=3):
    """ Return related datasets for a specific dataset

    :param id: Package (dataset) id
    :type id: string

    :param limit: Number of datasets to return. Default is 3.
    :type limit: integer

    :returns: a list of datasets related to a previously chosen dataset.
    :rtype: list

    """

    related_datasets = toolkit.get_action('datagovmk_get_related_datasets')(
        data_dict={'id': id, 'limit': limit}
    )

    return related_datasets

def get_groups():
    ''' This helper returns all the created groups sorted by the number of datasets desc without
    listing the empty ones

    :returns: a list of groups soted by the number of datasets per each group desc
    :rtype: list

    '''
    data_dict = {
        'sort': 'package_count',
        'all_fields': True,
        'include_extras': True
    }
    groups = _get_action('group_list', {}, data_dict)
    # groups = [group for group in groups if group.get('package_count') > 0]

    return groups


def get_dataset_stats(dataset_id):
    """Returns stats for the specified dataset.

    :param dataset_id: the id of the dataset.
    :type dataset_id: string

    :returns: the package stats. If no stats available, returns an empty dict.
      Available dict values are:\n
      ``id`` - the package id\n
      ``visits_recently`` - number of recent visits.\n
      ``visits_ever`` - total number of visits to this package.\n

    :rtype: dictionary

    """

    stats = get_stats_for_package(dataset_id)
    return stats


def get_resource_stats(resource_id):
    """Returns stats for the specified resource.

    :param resource_id: the id of the resource.
    :type resource_id: string

    :returns: the resource stats. If no stats available, returns an empty dict.
        Available dict values are:\n
        ``id`` - the package id\n
        ``visits_recently`` - number of recent visits.\n
        ``visits_ever`` - total number of visits to this package.\n
        ``downloads`` - total number of downloads of this resource.\n

    :rtype: dictionary

    """
    stats = get_stats_for_resource(resource_id)
    return stats


def get_package_total_downloads(package_id):
    """Returns the total number of dowloads of all resources that belong to this
    package.

    :param package_id: the id of the package(dataset).
    :type package_id: string

    :returns: the total number of downloads of all resources that belong to this package (dataset)
    :rtype: integer

    """
    return get_total_package_downloads(package_id)


def get_storage_path_for(dirname):
    """Returns the full path for the specified directory name within
    CKAN's storage path. If the target directory does not exists, it
    gets created.

    :param dirname: the directory name
    :type dirname: string

    :returns: a full path for the specified directory name within CKAN's storage path
    :rtype: string
    """
    storage_path = config.get('ckan.storage_path')
    target_path = os.path.join(storage_path, 'storage', dirname)
    print('::::: does it exist', target_path)
    print(os.path.exists(target_path))
    if not os.path.exists(target_path):
        print(":::::: target_path ---->", target_path)
        try:
            os.makedirs(target_path)
            print('OK _____+++++')
        except OSError as exc:
            log.error('Storage directory creation failed. Error: %s' % exc)
            target_path = os.path.join(storage_path, 'storage')
            if not os.path.exists(target_path):
                log.info('CKAN storage directory not found also')
                raise

    return target_path


def get_user_id(user_name):
    """ Get the user id from the user name
    :param user_name: the user name of the user
    :type user_name: str
    :returns: id of the user
    :rtype: str
    """

    try:
        user = toolkit.get_action('user_show')({}, {'id': user_name})
        return user.get('id')
    except:
        return None


def get_last_authority_for_user(authority_type, user_id):
    """ Get last authority file for the user
    :param authority_type: general or additional
    :type authority_type: str
    :param user_id: the id of the user
    :type user_id: str
    :returns: the last authority file for the user
    :rtype: str
    """
    user_authority = UserAuthority.get_last_authority_for_user(
        authority_type, user_id
    )

    return user_authority


def translate_field(data_dict, field_name):
    """ This function translates the field based on the current locale
    :param data_dict: data_dict which is the metadata of the dataset/organization/resource/group
    :type data_dict: dict
    :param field_name: the field that needs to be translated
    :type field_name: str
    :returns: the translated field
    :rtype: str
    """

    if isinstance(data_dict, dict):
        return core_helpers.get_translated(data_dict, field_name)


def get_org_title(id):
    """ Gets the translated title of the organization
    :param id: the id of the organization
    :type id: str
    returns: the translated title of the organization
    :rtype: str
    """

    org = toolkit.get_action('organization_show')(data_dict={'id': id})

    return translate_field(org, 'title')


def get_org_description(id):
    """ Gets the translated description of the organization
    :param id: the id of the organization
    :type id: str
    returns: the translated description of the organization
    :rtype: str
    """

    org = toolkit.get_action('organization_show')(data_dict={'id': id})

    return translate_field(org, 'description')

def get_org_title_desc(org):
    """ Gets the translated title and description of the organization
    :param org: the organization
    :type org: dict
    returns: the translated title and description of the organization
    :rtype: tuple
    """

    title = translate_field(org, 'title')
    description = translate_field(org, 'description')

    return title, description

def get_org_catalog(id):
    """ Get the catalog for an organization. A catalog is represented as a
    dataset.
    :param id: the id of the organization
    :type id: str
    :returns: the catalog for an organization
    :rtype: dict
    """
    try:
        data_dict = {
            'fq': '(owner_org:{0} AND extras_org_catalog_enabled:true)'.format(id)
        }
        data = toolkit.get_action('package_search')(data_dict=data_dict)
        return data['results'][0]
    except Exception:
        return None


def get_catalog_count(user):
    """ Count how many catalogs (datasets) are in the portal.
    :param user: The username of the user
    :type user: str
    :returns: totat number of catalogs
    :rtype: list
    """
    data_dict = {
        'fq': 'extras_org_catalog_enabled:true',
        'include_private': authz.is_sysadmin(user)
    }
    return toolkit.get_action('package_search')(data_dict=data_dict)['count']


def get_translated(json_str):
    """ Converts json to dict and gets the appropriate value for the current language

    :param json_str: the json with translates, example {'mk': '', 'en': '', 'sq': ''}
    :type json_str: str/unicode
    :returns: the appropriate value for the current language from the json
    :rtype: str
    """
    try:
        lang = i18n.get_lang()
        d = json.loads(json_str)
        return d.get(lang, None) if isinstance(d, dict) else ''
    except:
        return ''


def get_site_statistics(user):
    """ Count how many datasets, organizations and groups exist for particular user

    :param user: The username of the user
    :type user: str
    :returns: the dictionary containing number of datasets, organizations and groups
    :rtype: dict
    """

    stats = {}
    data_dict = {
        "rows": 1,
        'include_private': authz.is_sysadmin(user)
    }

    stats['dataset_count'] = toolkit.get_action('package_search')({}, data_dict)['count']
    stats['group_count'] = len(toolkit.get_action('group_list')({}, {}))
    stats['organization_count'] = len(toolkit.get_action('organization_list')({}, {}))

    return stats
    
def get_config_option_show(value_for, lang):

    if value_for == "about":
        if lang == "mk":
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_about_mk'
            })
        elif lang == "en":
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_about_en'
            })
        else:
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_about_sq'
            })
    elif value_for == "intro":
        if lang == "mk":
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_intro_text_mk'
            })
        elif lang == "en":
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_intro_text_en'
            })
        else:
            text = toolkit.get_action('config_option_show')({},{
                'key':'ckan.site_intro_text_sq'
            })
    return text 