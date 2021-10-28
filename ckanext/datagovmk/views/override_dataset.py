# encoding: utf-8
import os
import re
import pytz
import logging
import six
from collections import OrderedDict
from functools import partial
from six.moves.urllib.parse import urlencode
from datetime import datetime

from flask import Blueprint, make_response

from ckan.common import asbool
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
import ckan.model as model
import ckan.plugins as plugins
from ckan.plugins.toolkit import _, config, g, request, abort
from ckan.plugins import toolkit
from ckan.lib.search import SearchError, SearchQueryError
from ckan.views.dataset import (drill_down_url,
                                remove_field,
                                _sort_by,
                                _pager_url,
                                _encode_params,
                                _get_search_details,
                                _setup_template_variables,
                                _get_pkg_template)

from ckanext.datagovmk.helpers import get_storage_path_for

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
check_access = logic.check_access
get_action = logic.get_action

log = logging.getLogger(__name__)


override_dataset = Blueprint('override_dataset',
                             __name__,
                             url_prefix=u'/dataset',
                             url_defaults={u'package_type': u'dataset'})


def override_search(package_type):
    extra_vars = {}

    try:
        context = {
            u'model': model,
            u'user': g.user,
            u'auth_user_obj': g.userobj
        }
        check_access(u'site_read', context)
    except NotAuthorized:
        base.abort(403, _(u'Not authorized to see this page'))

    # unicode format (decoded from utf8)
    extra_vars[u'q'] = q = request.args.get(u'q', u'')

    extra_vars['query_error'] = False
    page = h.get_page_number(request.args)

    limit = int(config.get(u'ckan.datasets_per_page', 20))

    # most search operations should reset the page counter:
    params_nopage = [(k, v) for k, v in request.args.items(multi=True)
                     if k != u'page']

    extra_vars[u'drill_down_url'] = drill_down_url
    extra_vars[u'remove_field'] = partial(remove_field, package_type)

    sort_by = request.args.get(u'sort', None)
    params_nosort = [(k, v) for k, v in params_nopage if k != u'sort']

    extra_vars[u'sort_by'] = partial(_sort_by, params_nosort, package_type)

    if not sort_by:
        sort_by_fields = []
    else:
        sort_by_fields = [field.split()[0] for field in sort_by.split(u',')]
    extra_vars[u'sort_by_fields'] = sort_by_fields

    pager_url = partial(_pager_url, params_nopage, package_type)

    search_url_params = urlencode(_encode_params(params_nopage))
    extra_vars[u'search_url_params'] = search_url_params

    details = _get_search_details()
    extra_vars[u'fields'] = details[u'fields']
    extra_vars[u'fields_grouped'] = details[u'fields_grouped']
    fq = details[u'fq']
    search_extras = details[u'search_extras']

    context = {
        u'model': model,
        u'session': model.Session,
        u'user': g.user,
        u'for_view': True,
        u'auth_user_obj': g.userobj
    }

    # Unless changed via config options, don't show other dataset
    # types any search page. Potential alternatives are do show them
    # on the default search page (dataset) or on one other search page
    search_all_type = config.get(u'ckan.search.show_all_types', u'dataset')
    search_all = False

    try:
        # If the "type" is set to True or False, convert to bool
        # and we know that no type was specified, so use traditional
        # behaviour of applying this only to dataset type
        search_all = asbool(search_all_type)
        search_all_type = u'dataset'
    # Otherwise we treat as a string representing a type
    except ValueError:
        search_all = True

    if not search_all or package_type != search_all_type:
        # Only show datasets of this particular type
        fq += u' +dataset_type:{type}'.format(type=package_type)

    facets = OrderedDict()

    default_facet_titles = {
        u'organization': _(u'Organizations'),
        u'groups': _(u'Groups'),
        u'tags': _(u'Tags'),
        u'res_format': _(u'Formats'),
        u'license_id': _(u'Licenses'),
    }

    for facet in h.facets():
        if facet in default_facet_titles:
            facets[facet] = default_facet_titles[facet]
        else:
            facets[facet] = facet

    # Facet titles
    for plugin in plugins.PluginImplementations(plugins.IFacets):
        facets = plugin.dataset_facets(facets, package_type)

    # Date interval search

    start_date = None
    end_date = None

    if request.args.get('_start_date'):
        start_date = extract_date(request.args.get('_start_date'))
        if start_date:
            extra_vars['start_date'] = request.args.get('_start_date')

    if request.args.get('_end_date'):
        end_date = extract_date(request.args.get('_end_date'))
        if end_date:
            extra_vars['end_date'] = request.args.get('_end_date')

    if start_date or end_date:
        if not start_date:
            start_date = datetime(year=1900, month=1, day=1)
        if not end_date:
            end_date = datetime(year=2100,
                                month=1,
                                day=1,
                                hour=23,
                                minute=59,
                                second=59,
                                microsecond=999999)
        else:
            end_date = datetime_to_utc(end_date)
            end_date = end_date.replace(hour=23,
                                        minute=59,
                                        second=59,
                                        microsecond=999999)

        s_date = datetime_to_utc(start_date).strftime('%Y-%m-%dT%H:%M:%SZ')
        e_date = datetime_to_utc(end_date).strftime('%Y-%m-%dT%H:%M:%SZ')
        fq += ' +metadata_modified:[{s_date} TO {e_date}]'\
            .format(s_date=s_date, e_date=e_date)

    extra_vars[u'facet_titles'] = facets
    data_dict = {
        u'q': q,
        u'fq': fq.strip(),
        u'facet.field': list(facets.keys()),
        u'rows': limit,
        u'start': (page - 1) * limit,
        u'sort': sort_by,
        u'extras': search_extras,
        u'include_private': asbool(
            config.get(u'ckan.search.default_include_private', True)
        ),
    }
    try:
        query = get_action(u'package_search')(context, data_dict)

        extra_vars[u'sort_by_selected'] = query[u'sort']

        extra_vars[u'page'] = h.Page(
            collection=query[u'results'],
            page=page,
            url=pager_url,
            item_count=query[u'count'],
            items_per_page=limit
        )
        extra_vars[u'search_facets'] = query[u'search_facets']
        extra_vars[u'page'].items = query[u'results']
    except SearchQueryError as se:
        # User's search parameters are invalid, in such a way that is not
        # achievable with the web interface, so return a proper error to
        # discourage spiders which are the main cause of this.
        log.info(u'Dataset search query rejected: %r', se.args)
        base.abort(
            400,
            _(u'Invalid search query: {error_message}')
            .format(error_message=str(se))
        )
    except SearchError as se:
        # May be bad input from the user, but may also be more serious like
        # bad code causing a SOLR syntax error, or a problem connecting to
        # SOLR
        log.error(u'Dataset search error: %r', se.args)
        extra_vars[u'query_error'] = True
        extra_vars[u'search_facets'] = {}
        extra_vars[u'page'] = h.Page(collection=[])

    # FIXME: try to avoid using global variables
    g.search_facets_limits = {}
    for facet in extra_vars[u'search_facets'].keys():
        try:
            limit = int(
                request.args.get(
                    u'_%s_limit' % facet,
                    int(config.get(u'search.facets.default', 10))
                )
            )
        except ValueError:
            base.abort(
                400,
                _(u'Parameter u"{parameter_name}" is not '
                  u'an integer').format(parameter_name=u'_%s_limit' % facet)
            )

        g.search_facets_limits[facet] = limit

    _setup_template_variables(context, {}, package_type=package_type)

    extra_vars[u'dataset_type'] = package_type

    # TODO: remove
    for key, value in six.iteritems(extra_vars):
        setattr(g, key, value)

    return base.render(
        _get_pkg_template(u'search_template', package_type), extra_vars
    )


def extract_date(datestr):
    """
    Change format of the date. Example: 01-08-2018 to 2018-08-01 00:00:00
    :param datestr: the date string which needs to be converted in
    different format
    :type datestr: str
    :returns: formatted string
    :rtype: str
    """

    datestr = datestr.strip() if datestr else ''
    m = re.match(r'(?P<dd>\d{1,2})[-/](?P<mm>\d{1,2})(?P<sep>[-/])(?P<yyyy>\d{4})', datestr)
    if m:
        if int(m.group('mm')) > 12:
            return _strptime('%m/%d/%Y' if m.group('sep') == '/'
                             else '%m-%d-%Y', datestr)
        else:
            return _strptime('%d/%m/%Y' if m.group('sep') == '/'
                             else '%d-%m-%Y', datestr)

    if re.match(r'\d{4}-\d{2}-\d{2}', datestr):
        return _strptime('%Y-%m-%d', datestr)

    return None


def _strptime(format_, datestr):
    try:
        return datetime.strptime(datestr, format_)
    except Exception:
        return None


def datetime_to_utc(dt):
    """Convert datetime to UTC
    :param dt: datetime
    :type dt: datetime
    :returns: converted datetime to UTC
    :rtype: datetime
    """
    return dt.replace(tzinfo=pytz.UTC)


def download_zip(zip_id):
    response = make_response()

    if not zip_id:
        abort(404, toolkit._('Resource data not found'))
    file_name, package_name = zip_id.split('::')
    file_path = get_storage_path_for('temp-datagovmk/' + file_name)

    if not os.path.isfile(file_path):
        abort(404, toolkit._('Resource data not found'))

    if not package_name:
        package_name = 'resources'
    package_name += '.zip'

    with open(file_path, 'r') as f:
        response.stream.write(f.read())

    response.headers['Content-Type'] = 'application/octet-stream'
    response.headers['Content-disposition'] =\
        'attachment; filename=' + package_name
    os.remove(file_path)


override_dataset.add_url_rule('/', view_func=override_search, methods=["GET"])
override_dataset.add_url_rule('/download/zip/<zip_id>',
                              view_func=download_zip,
                              methods=["GET", "POST"])
