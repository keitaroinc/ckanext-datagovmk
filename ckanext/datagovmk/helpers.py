from ckan.plugins import toolkit
from ckan.lib import search
from datetime import datetime

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

def get_groups():
    # Helper used on the homepage for showing groups

    data_dict = {
        'sort': 'package_count',
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)
    groups = [group for group in groups if group.get('package_count') > 0]

    return groups
