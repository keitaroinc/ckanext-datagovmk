"""datagovmk custom helpers.
"""
import os
import time

from ckan.plugins import toolkit
from ckan.lib import search
from datetime import datetime
from ckan.common import config
from ckanext.datagovmk.model.stats import (get_stats_for_package,
                                           get_stats_for_resource,
                                           get_total_package_downloads)

from logging import getLogger
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckan.lib import helpers as core_helpers

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

    start_time = time.time()

    try:
        pkg_search_results = toolkit.get_action('package_search')(data_dict={
            'sort': 'metadata_modified desc',
            'rows': limit,
        })['results']

    except toolkit.ValidationError, search.SearchError:
        print("get_recently_updated_datasets:  %s seconds " % (time.time() - start_time))
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
        print("get_recently_updated_datasets:  %s seconds " % (time.time() - start_time))
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
    start_time = time.time()

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

    print("get_most_active_organizations:  %s seconds " %
             (time.time() - start_time))

    return orgs[:limit]


def get_related_datasets(id, limit=3):
    """ Return related datasets for a specific dataset

    :param id: Package (dataset) id
    :type id: string

    :param limit: Number of datasets to return. Default is 3.
    :type limit: integer

    :returns: a list of datasets related to a previously chosen dataset.
    :rtype: list

    """
    start_time = time.time()

    related_datasets = toolkit.get_action('datagovmk_get_related_datasets')(
        data_dict={'id': id, 'limit': limit}
    )

    print("get_related_datasets:  %s seconds " %
             (time.time() - start_time))

    return related_datasets

def get_groups():
    ''' This helper returns all the created groups sorted by the number of datasets desc without
    listing the empty ones

    :returns: a list of groups soted by the number of datasets per each group desc
    :rtype: list

    '''

    start_time = time.time()

    data_dict = {
        'sort': 'package_count',
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)
    groups = [group for group in groups if group.get('package_count') > 0]

    print("get_groups:  %s seconds " %
                (time.time() - start_time))

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
    start_time =  time.time()

    stats = get_stats_for_package(dataset_id)

    print("get_dataset_stats:  %s seconds " %
             (time.time() - start_time))

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
    start_time = time.time()

    stats = get_stats_for_resource(resource_id)

    print("get_resource_stats:  %s seconds " %
             (time.time() - start_time))

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
    start_time = time.time()
    storage_path = config.get('ckan.storage_path')
    target_path = os.path.join(storage_path, 'storage', dirname)
    if not os.path.exists(target_path):
        try:
            os.makedirs(target_path)
        except OSError, exc:
            log.error('Storage directory creation failed. Error: %s' % exc)
            target_path = os.path.join(storage_path, 'storage')
            if not os.path.exists(target_path):
                print('CKAN storage directory not found also')
                raise

    print("get_storage_path_for:  %s seconds " %
             (time.time() - start_time))

    return target_path


def get_user_id(user_name):
    """ Get the user id from the user name
    :param user_name: the user name of the user
    :type user_name: str
    :returns: id of the user
    :rtype: str
    """
    start_time=time.time()
    try:
        user = toolkit.get_action('user_show')({}, {'id': user_name})

        print("get_user_id:  %s seconds " %
                    (time.time() - start_time))

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
    start_time = time.time()
    user_authority = UserAuthority.get_last_authority_for_user(
        authority_type, user_id
    )

    print("get_last_authority_for_user:  %s seconds " %
                (time.time() - start_time))

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
    start_time = time.time()
    org = toolkit.get_action('organization_show')(data_dict={'id': id})

    title = translate_field(org, 'title')

    print("get_org_title:  %s seconds " %
             (time.time() - start_time))

    return title


def get_org_title_desc(id):
    """ Gets the translated title and description of the organization
    :param id: the id of the organization
    :type id: str
    returns: the translated title and description of the organization
    :rtype: tuple
    """

    start_time = time.time()

    org = toolkit.get_action('organization_show')(data_dict={'id': id})

    title = translate_field(org, 'title')
    description = translate_field(org, 'description')

    print("get_org_title_desc:  %s seconds " %
              (time.time() - start_time))

    return title, description

def get_org_description(id):
    """ Gets the translated description of the organization
    :param id: the id of the organization
    :type id: str
    returns: the translated description of the organization
    :rtype: str
    """
    start_time = time.time()
    org = toolkit.get_action('organization_show')(data_dict={'id': id})

    description = translate_field(org, 'description')

    print("get_org_description:  %s seconds " %
             (time.time() - start_time))

    return description


def get_org_catalog(id):
    """ Get the catalog for an organization. A catalog is represented as a
    dataset.
    :param id: the id of the organization
    :type id: str
    :returns: the catalog for an organization
    :rtype: dict
    """
    start_time = time.time()
    try:
        data_dict = {
            'fq': '(owner_org:{0} AND extras_org_catalog_enabled:true)'.format(id)
        }
        data = toolkit.get_action('package_search')(data_dict=data_dict)
        print("get_org_catalog:  %s seconds " %
                    (time.time() - start_time))

        return data['results'][0]
    except Exception:
        print("get_org_catalog:  %s seconds " %
                    (time.time() - start_time))

        return None


def get_catalog_count():
    """ Count how many catalogs (datasets) are in the portal.
    :returns: totat number of catalogs
    :rtype: list
    """
    start_time = time.time()

    data_dict = {
        'fq': 'extras_org_catalog_enabled:true'
    }
    count = toolkit.get_action('package_search')(data_dict=data_dict)['count']

    print("get_catalog_count:  %s seconds " %
                (time.time() - start_time))

    return count
