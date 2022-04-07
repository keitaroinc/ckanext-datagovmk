from flask import Blueprint
from logging import getLogger
import ckan.plugins as p
import ckan.lib.helpers as h
from ckanext.datagovmk import stats as stats_lib

log = getLogger(__name__)

override_stats = Blueprint('override_stats', __name__)


def index():
    stats = stats_lib.Stats()
    extra_vars = {
        'largest_groups': stats.largest_groups(),
        'top_tags': stats.top_tags(),
        'top_package_creators': stats.top_package_creators(),
        'top_rated_packages': stats.top_rated_packages(),
        'most_edited_packages': stats.most_edited_packages(),
        'new_packages_by_week': stats.get_by_week('new_packages'),
        'deleted_packages_by_week': stats.get_by_week('deleted_packages'),
        'num_packages_by_week': stats.get_num_packages_by_week(),
        'package_revisions_by_week': stats.get_by_week('package_revisions')
    }

    extra_vars['raw_packages_by_week'] = []
    for week_date, num_packages, cumulative_num_packages\
            in stats.get_num_packages_by_week():
        extra_vars['raw_packages_by_week'].append(
            {'date': h.date_str_to_datetime(week_date),
             'total_packages': cumulative_num_packages})

    extra_vars['raw_all_package_revisions'] = []
    for week_date, revs, num_revisions, cumulative_num_revisions\
            in stats.get_by_week('package_revisions'):
        extra_vars['raw_all_package_revisions'].append(
            {'date': h.date_str_to_datetime(week_date),
             'total_revisions': num_revisions})

    extra_vars['raw_new_datasets'] = []
    for week_date, pkgs, num_packages, cumulative_num_revisions\
            in stats.get_by_week('new_packages'):
        extra_vars['raw_new_datasets'].append(
            {'date': h.date_str_to_datetime(week_date),
             'new_packages': num_packages})

    extra_vars['raw_deleted_datasets'] = []
    for week_date, pkgs, num_packages, cumulative_num_packages\
            in stats.get_by_week('deleted_packages'):
        extra_vars['raw_deleted_datasets'].append(
            {'date': h.date_str_to_datetime(
                week_date), 'deleted_packages': num_packages})

    return p.toolkit.render(u'ckanext/stats/index.html', extra_vars)


override_stats.add_url_rule('/stats', view_func=index, methods=["GET"])
