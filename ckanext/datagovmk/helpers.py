"""datagovmk custom helpers.
"""
import os

from ckan.plugins import toolkit
from ckan.lib import search
from datetime import datetime
from ckan.common import config
from ckanext.datagovmk.model.stats import (get_stats_for_package,
                                           get_stats_for_resource,
                                           get_total_package_downloads)

from logging import getLogger
log = getLogger(__name__)

def _get_action(action, context_dict, data_dict):
    return toolkit.get_action(action)(context_dict, data_dict)

def get_recently_updated_datasets(limit=5):
    '''
     Returns recent created or updated datasets.

    :param limit: Limit of the datasets to be returned
    :return: list
    '''
    try:
        pkg_search_results = toolkit.get_action('package_search')(data_dict={
            'sort': 'metadata_modified desc',
            'rows': limit,
        })['results']

    except toolkit.ValidationError, search.SearchError:
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
    Returns most active organizations by number of datasets published

    :param limit: Number of organizations to be returned
    :return list
    '''
    organizatons = toolkit.get_action('organization_list')(data_dict={
        'all_fields': True,
        'order_by': 'packages',
        'limit': limit
    })
    return organizatons

def get_related_datasets(id, limit=3):
    """ Return related datasets for a specific dataset

    :param id: Dataset id
    :param limit: Number of datasets to return. Default is 3.
    :return list of datasets
    """

    related_datasets = toolkit.get_action('datagovmk_get_related_datasets')(
        data_dict={'id': id, 'limit': limit}
    )

    return related_datasets

# Helper used on the homepage for showing groups

def get_groups():

    data_dict = {
        'sort': 'package_count',
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)
    groups = [group for group in groups if group.get('package_count') > 0]

    return groups


def get_dataset_stats(dataset_id):
    """Returns stats for the specified dataset.

    :param str dataset_id: the id of the dataset.

    :return dict
    """
    stats = get_stats_for_package(dataset_id)
    return stats


def get_resource_stats(resource_id):
    """Returns stats for the specified resource.

    :param str resource_id: the id of the resource.

    :return dict
    """
    stats = get_stats_for_resource(resource_id)
    return stats


def get_package_total_downloads(package_id):
    """Returns the total number of dowloads of all resources that belong to this
    package.

    :param str package_id: the id of the package(dataset).

    :return int
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
    if not os.path.exists(target_path):
        try:
            os.makedirs(target_path)
        except OSError, exc:
            log.error('Storage directory creation failed. Error: %s' % exc)
            target_path = os.path.join(storage_path, 'storage')
            if not os.path.exists(target_path):
                log.info('CKAN storage directory not found also')
                raise

    return target_path
