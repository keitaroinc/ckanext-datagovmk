"""datagovmk custom helpers.
"""
from ckan.plugins import toolkit
from ckan.lib import search
from datetime import datetime

from ckanext.datagovmk.model.stats import (get_stats_for_package,
                                           get_stats_for_resource,
                                           get_total_package_downloads)

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

    :param limit: Number of organizations to be returned. Default is 5.
    :type limit: integer

    :returns: a list of the most active organizations.
    :rtype: list

    '''
    organizatons = toolkit.get_action('organization_list')(data_dict={
        'all_fields': True,
        'order_by': 'packages',
        'limit': limit
    })
    return organizatons

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
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)
    groups = [group for group in groups if group.get('package_count') > 0]

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