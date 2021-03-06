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

"""Controllers definitions and overrides.
"""
import os
import paste.fileapp
import mimetypes
import uuid
import zipfile
from logging import getLogger
import json
import csv
import re
from urllib import urlencode
import pytz
from io import StringIO


from ckan.common import config
from paste.deploy.converters import asbool

from ckan.controllers.package import PackageController, search_url, _encode_params
from ckan.controllers.user import UserController
from ckanext.datagovmk.helpers import get_storage_path_for
from ckanext.datagovmk.utils import (export_resource_to_rdf,
                                     export_resource_to_xml,
                                     export_dict_to_csv,
                                     to_utf8_str,
                                     export_package_to_xml,
                                     export_package_to_rdf,
                                     send_email)
from ckanext.datagovmk.lib import (verify_activation_link,
                                   create_activation_key)
from ckanext.datagovmk.actions import update_package_stats
from ckan.lib.base import BaseController, abort, render
from ckan.plugins import toolkit
import ckan.plugins as p
from ckan.common import _, c, request, response, config, OrderedDict
from ckan.lib.navl import dictization_functions

import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h
from ckan.controllers.admin import get_sysadmins
import bleach
from datetime import datetime
import ckan.lib.captcha as captcha

from ckanext.datastore.controller import (DatastoreController,
                                          int_validator,
                                          boolean_validator,
                                          DUMP_FORMATS,
                                          PAGINATE_BY)
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
)

from contextlib import contextmanager
from email.utils import encode_rfc2231

from xml.etree.cElementTree import Element, SubElement, ElementTree
from six import text_type

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
DataError = dictization_functions.DataError

get_action = logic.get_action
check_access = logic.check_access

unflatten = dictization_functions.unflatten

log = getLogger(__name__)


SPECIAL_CHARS = u'#$%&!?\/@}{[]'


class DownloadController(PackageController):
    """Overrides CKAN's PackageController to add count for the resource downloads.
    """

    def download_zip(self, zip_id):
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
            response.write(f.read())

        response.headers['Content-Type'] = 'application/octet-stream'
        response.content_disposition = 'attachment; filename=' + package_name
        os.remove(file_path)

    def search(self):
        from ckan.lib.search import SearchError, SearchQueryError

        package_type = self._guess_package_type()

        extra_vars={'dataset_type': package_type}

        try:
            context = {'model': model, 'user': c.user,
                       'auth_user_obj': c.userobj}
            check_access('site_read', context)
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        # unicode format (decoded from utf8)
        q = c.q = request.params.get('q', u'')
        c.query_error = False
        page = h.get_page_number(request.params)

        limit = int(config.get('ckan.datasets_per_page', 20))

        # most search operations should reset the page counter:
        params_nopage = [(k, v) for k, v in request.params.items()
                         if k != 'page']

        def drill_down_url(alternative_url=None, **by):
            return h.add_url_param(alternative_url=alternative_url,
                                   controller='package', action='search',
                                   new_params=by)

        c.drill_down_url = drill_down_url

        def remove_field(key, value=None, replace=None):
            return h.remove_url_param(key, value=value, replace=replace,
                                      controller='package', action='search',
                                      alternative_url=package_type)

        c.remove_field = remove_field

        sort_by = request.params.get('sort', None)
        params_nosort = [(k, v) for k, v in params_nopage if k != 'sort']

        def _sort_by(fields):
            """
            Sort by the given list of fields.

            Each entry in the list is a 2-tuple: (fieldname, sort_order)

            eg - [('metadata_modified', 'desc'), ('name', 'asc')]

            If fields is empty, then the default ordering is used.
            """
            params = params_nosort[:]

            if fields:
                sort_string = ', '.join('%s %s' % f for f in fields)
                params.append(('sort', sort_string))
            return search_url(params, package_type)

        c.sort_by = _sort_by
        if not sort_by:
            c.sort_by_fields = []
        else:
            c.sort_by_fields = [field.split()[0]
                                for field in sort_by.split(',')]

        def pager_url(q=None, page=None):
            params = list(params_nopage)
            params.append(('page', page))
            return search_url(params, package_type)

        c.search_url_params = urlencode(_encode_params(params_nopage))

        try:
            c.fields = []
            # c.fields_grouped will contain a dict of params containing
            # a list of values eg {'tags':['tag1', 'tag2']}
            c.fields_grouped = {}
            search_extras = {}
            fq = ''
            for (param, value) in request.params.items():
                if param not in ['q', 'page', 'sort'] \
                        and len(value) and not param.startswith('_'):
                    if not param.startswith('ext_'):
                        c.fields.append((param, value))
                        fq += ' %s:"%s"' % (param, value)
                        if param not in c.fields_grouped:
                            c.fields_grouped[param] = [value]
                        else:
                            c.fields_grouped[param].append(value)
                    else:
                        search_extras[param] = value

            context = {'model': model, 'session': model.Session,
                       'user': c.user, 'for_view': True,
                       'auth_user_obj': c.userobj}

            # Unless changed via config options, don't show other dataset
            # types any search page. Potential alternatives are do show them
            # on the default search page (dataset) or on one other search page
            search_all_type = config.get(
                                  'ckan.search.show_all_types', 'dataset')
            search_all = False

            try:
                # If the "type" is set to True or False, convert to bool
                # and we know that no type was specified, so use traditional
                # behaviour of applying this only to dataset type
                search_all = asbool(search_all_type)
                search_all_type = 'dataset'
            # Otherwise we treat as a string representing a type
            except ValueError:
                search_all = True

            if not package_type:
                package_type = 'dataset'

            if not search_all or package_type != search_all_type:
                # Only show datasets of this particular type
                fq += ' +dataset_type:{type}'.format(type=package_type)

            facets = OrderedDict()

            default_facet_titles = {
                'organization': _('Organizations'),
                'groups': _('Groups'),
                'tags': _('Tags'),
                'res_format': _('Formats'),
                'license_id': _('Licenses'),
                }

            for facet in h.facets():
                if facet in default_facet_titles:
                    facets[facet] = default_facet_titles[facet]
                else:
                    facets[facet] = facet

            # Facet titles
            for plugin in p.PluginImplementations(p.IFacets):
                facets = plugin.dataset_facets(facets, package_type)

            c.facet_titles = facets

            # Date interval search

            start_date = None
            end_date = None

            if request.params.get('_start_date'):
                start_date = extract_date(request.params.get('_start_date'))
                if start_date:
                    extra_vars['start_date'] = request.params.get('_start_date')

            if request.params.get('_end_date'):
                end_date = extract_date(request.params.get('_end_date'))
                if end_date:
                    extra_vars['end_date'] = request.params.get('_end_date')

            if start_date or end_date:
                if not start_date:
                    start_date = datetime(year=1900, month=1, day=1)
                if not end_date:
                    end_date = datetime(year=2100, month=1, day=1, hour=23, minute=59,second=59, microsecond=999999)
                else:
                    end_date = datetime_to_utc(end_date)
                    end_date = end_date.replace(hour=23, minute=59,second=59, microsecond=999999)

                fq = fq + ' +metadata_modified:[%s TO %s]' % (datetime_to_utc(start_date).strftime('%Y-%m-%dT%H:%M:%SZ'),
                                                              datetime_to_utc(end_date).strftime('%Y-%m-%dT%H:%M:%SZ'))

            data_dict = {
                'q': q,
                'fq': fq.strip(),
                'facet.field': facets.keys(),
                'rows': limit,
                'start': (page - 1) * limit,
                'sort': sort_by,
                'extras': search_extras,
                'include_private': asbool(config.get(
                    'ckan.search.default_include_private', True)),
            }

            query = get_action('package_search')(context, data_dict)
            c.sort_by_selected = query['sort']

            c.page = h.Page(
                collection=query['results'],
                page=page,
                url=pager_url,
                item_count=query['count'],
                items_per_page=limit
            )
            c.search_facets = query['search_facets']
            c.page.items = query['results']
        except SearchQueryError as se:
            # User's search parameters are invalid, in such a way that is not
            # achievable with the web interface, so return a proper error to
            # discourage spiders which are the main cause of this.
            log.info('Dataset search query rejected: %r', se.args)
            abort(400, _('Invalid search query: {error_message}')
                  .format(error_message=str(se)))
        except SearchError as se:
            # May be bad input from the user, but may also be more serious like
            # bad code causing a SOLR syntax error, or a problem connecting to
            # SOLR
            log.error('Dataset search error: %r', se.args)
            c.query_error = True
            c.search_facets = {}
            c.page = h.Page(collection=[])
        except NotAuthorized:
            abort(403, _('Not authorized to see this page'))

        c.search_facets_limits = {}
        for facet in c.search_facets.keys():
            try:
                limit = int(request.params.get('_%s_limit' % facet,
                            int(config.get('search.facets.default', 10))))
            except ValueError:
                abort(400, _('Parameter "{parameter_name}" is not '
                             'an integer').format(
                      parameter_name='_%s_limit' % facet))
            c.search_facets_limits[facet] = limit

        self._setup_template_variables(context, {},
                                       package_type=package_type)

        extra_vars['dataset_type'] = package_type
        return render(self._search_template(package_type),
                      extra_vars=extra_vars)


class ApiController(BaseController):
    def i18n_js_translations(self, lang):
        ''' Patch for broken JS translations caused by Pylons to Flask
        migration. This method patches https://github.com/ckan/ckan/blob/master/ckan/views/api.py#L467

        :param lang: locale of the language
        :type lang: string

        :returns: the translated strings in a json file.

        :rtype: json

        '''

        ckan_path = config.get('ckan.path')
        if ckan_path is None:
            ckan_path = os.path.join(
                os.path.dirname(__file__), '..', '..', '..', 'ckan', 'ckan'
            )
            source = os.path.abspath(os.path.join(ckan_path, 'public',
                                    'base', 'i18n', '%s.js' % lang))
        else:
            source = os.path.join(config.get('ckan.path'), 'ckan', 'public',
                                    'base', 'i18n', '%s.js' % lang)
        toolkit.response.headers['Content-Type'] =\
            'application/json;charset=utf-8'
        if not os.path.exists(source):
            return '{}'
        f = open(source, 'r')
        return(f)


class BulkDownloadController(BaseController):
    """Download metadata as ZIP file.
    """

    def download_resources_metadata(self, package_id):
        """Download resources metadata in different formats as ZIP file.

        :param str package_id: the id of the package containing the resources.

        """
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}


        pkg_dict = get_action('package_show')(context, {'id': package_id})

        resources = request.params.get('resources')
        if resources and resources.lower() != 'all':
            resources = [r.strip() for r in resources.split(',')]
        else:
            resources = None

        tmp_file_path = None
        try:
            with _open_temp_zipfile() as zipf:
                tmp_file_path = zipf.filename
                self._export_resources(zipf, pkg_dict, resources)
        except Exception as exc:
            log.error('Error while preparing zip archive: %s', exc)
            log.exception(exc)
            raise exc

        try:
            response.headers['Content-Type'] = 'application/octet-stream'
            zip_file_name = '%s_resources.zip' % pkg_dict['name']
            response.content_disposition = 'attachment; filename=' + zip_file_name
            with open(tmp_file_path, 'r') as zipf:
                response.write(zipf.read())
        finally:
            os.remove(tmp_file_path)

    def _export_resources(self, zip_file, pkg_dict, resources):
        format = request.params.get('format', 'json')
        exporter = _SUPPORTED_EXPORTS.get(format)
        if not exporter:
            raise Exception('Unsupported export format: %s' % format)
        # filter out resources first
        if resources:
            filtered_resources = []
            for resource in pkg_dict.get('resources', []):
                if resource['id'] in resources:
                    filtered_resources.append(resource)

            pkg_dict['resources'] = filtered_resources

        exporter(zip_file, pkg_dict, request, response)

    def download_package_metadata(self, package_id):
        """Download package metadata in one of the supported formats.

        :param string package_id: the id of the package

        """

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        package_dict = get_action('package_show')(context, {'id': package_id})
        _format = request.params.get('format', 'json')
        export_def = _SUPPORTED_PACKAGE_EXPORTS.get(_format)
        if not export_def:
            raise Exception('Unsupported export format: %s' % _format)

        content_type = export_def['content-type']
        response.headers['Content-Type'] = content_type

        exporter = export_def['exporter']

        file_name = '%s.%s' % (package_dict.get('name') or package_dict['id'], _format)

        response.content_disposition = 'attachment; filename=' + file_name
        response.charset = 'UTF-8'

        exporter(package_dict, request, response)


class DatagovmkUserController(UserController):
    """Overrides CKAN's UserController to send activation email to the user."""

    def datagovmk_register(self, data=None, errors=None, error_summary=None):
        """ Wrapper around UserController's register method"""

        return self.register(data, errors, error_summary)

    def perform_activation(self, id):
        """ Activates user account

        :param id: user ID
        :type id: string

        """

        context = {'model': model, 'session': model.Session,
                   'user': id, 'keep_email': True}

        try:
            data_dict = {'id': id}
            user_dict = get_action('user_show')(context, data_dict)

            user_obj = context['user_obj']
        except NotFound, e:
            abort(404, _('User not found'))

        c.activation_key = request.params.get('key')
        if not verify_activation_link(user_obj, c.activation_key):
            h.flash_error(_('Invalid activation key. Please try again.'))
            abort(403)

        try:
            user_dict['reset_key'] = c.activation_key
            user_dict['state'] = model.State.ACTIVE
            user = get_action('user_update')(context, user_dict)
            create_activation_key(user_obj)

            h.flash_success(_('Your account has been activated.'))
            h.redirect_to(controller='user', action='login')
        except NotAuthorized:
            h.flash_error(_('Unauthorized to edit user %s') % id)
        except NotFound, e:
            h.flash_error(_('User not found'))
        except DataError:
            h.flash_error(_(u'Integrity Error'))
        except ValidationError, e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError, ve:
            h.flash_error(unicode(ve))

        c.user_dict = user_dict
        h.redirect_to(controller='user', action='login')

    def _save_new(self, context):
        came_from = request.params.get('came_from')
        try:
            data_dict = logic.clean_dict(unflatten(
                logic.tuplize_dict(logic.parse_params(request.params))))
            context['message'] = data_dict.get('log_message', '')
            captcha.check_recaptcha(request)
            user = get_action('user_create')(context, data_dict)
        except NotAuthorized:
            abort(403, _('Unauthorized to create user %s') % '')
        except NotFound, e:
            abort(404, _('User not found'))
        except DataError:
            abort(400, _(u'Integrity Error'))
        except captcha.CaptchaError:
            error_msg = _(u'Bad Captcha. Please try again.')
            h.flash_error(error_msg)
            return self.new(data_dict)
        except ValidationError, e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.new(data_dict, errors, error_summary)

        h.flash_success(_('A confirmation email has been sent to %s. '
                          'Please use the link in the email to continue.') %
                          data_dict['email'])
        if not c.user:
            # Do not log in the user programatically
            # set_repoze_user(data_dict['name'])
            if came_from:
                h.redirect_to(came_from)
            else:
                # redirect user to login page
                # h.redirect_to(controller='user', action='me')
                h.redirect_to(controller='user', action='login')
        else:
            h.flash_success(_('User %s is now registered but you are still '
                            'logged in as %s from before') %
                            (data_dict['name'], c.user))
            if authz.is_sysadmin(c.user):
                h.redirect_to(controller='user',
                                action='activity',
                                id=data_dict['name'])
            else:
                return render('user/logout_first.html')


def _export_resources_json(zip_file, pkg_dict, request, response):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        rc_filename = u'%s.json' % resource_name
        zip_file.writestr(rc_filename.encode('utf-8'), json.dumps(resource, indent=4, ensure_ascii=False).encode('utf-8'))


def _export_to_rdf(zip_file, pkg_dict, request, response, file_ext='rdf'):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        file_name = u'%s.rdf' % resource_name

        output = export_resource_to_rdf(resource, pkg_dict)
        zip_file.writestr(file_name.encode('utf-8'), output)


def _export_resources_rdf(zip_file, pkg_dict, request, response):
    return _export_to_rdf(zip_file, pkg_dict, request, response, 'rdf')


def _export_resources_xml(zip_file, pkg_dict, request, response):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True
        file_name = u'%s.xml' % resource_name
        output = export_resource_to_xml(resource)
        zip_file.writestr(file_name.encode('utf-8'), output.encode('utf-8'))


def _export_resources_csv(zip_file, pkg_dict, request, response):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        rc_filename =to_utf8_str('%s.csv' % resource_name)
        output = export_dict_to_csv(resource)
        zip_file.writestr(rc_filename, output)

_SUPPORTED_EXPORTS = {
    'json': _export_resources_json,
    'rdf': _export_resources_rdf,
    'xml': _export_resources_xml,
    'csv': _export_resources_csv
}


def _export_package_json(package_dict, request, response):
    json.dump(package_dict, response, indent=4, ensure_ascii=False)


def _export_package_xml(package_dict, request, response):
    response.write(export_package_to_xml(package_dict))


def _export_package_to_rdf(package_dict, request, response):
    response.write(export_package_to_rdf(package_dict, _format='xml'))


def _export_package_to_csv(package_dict, request, response):
    result = {}
    for key, value in package_dict.iteritems():
        if isinstance(value, list):
            if not value:
                value = ""
            elif len(value) == 1:
                value = value[0]
        result[key] = value

    if result.get('organization'):
        result['organization'] = result['organization'].get('name') or result['organization']['id']

    if result.get('tags'):
        tags = []
        for tag in result['tags']:
            tags.append(tag.get('name') or tag['id'])
        result['tags'] = ','.join(tags)

    response.write(export_dict_to_csv(result))


_SUPPORTED_PACKAGE_EXPORTS = {
    'json': {
        'content-type': 'application/json',
        'exporter': _export_package_json,
    },
    'rdf': {
        'content-type': 'application/rdf+xml',
        'exporter': _export_package_to_rdf,
    },
    'xml': {
        'content-type': 'application/xml',
        'exporter': _export_package_xml,
    },
    'csv': {
        'content-type': 'text/csv',
        'exporter': _export_package_to_csv,
    },
}


def _open_temp_zipfile():
    file_name = uuid.uuid4().hex + '.{ext}'.format(ext='zip')
    file_path = get_storage_path_for('temp-datagovmk') + '/' + file_name


    return zipfile.ZipFile(file_path, 'w')


class ReportIssueController(BaseController):
    """Controller for the issue reporting (site wide) form.
    """
    def report_issue_form(self):
        """Renders the issue reporting form and reports the issue by sending
        an email to the system admin with the issue.
        """
        login_required = False
        if not c.user:
            login_required = True

        data_dict = {}
        errors = {
            'issue_title': [],
            'issue_description': []
        }
        extra_vars = {
            'data': data_dict,
            'errors': errors,
            'login_required': login_required
        }
        if request.method == 'POST':
            data_dict['issue_title'] = request.params.get('issue_title')
            data_dict['issue_description'] = request.params.get('issue_description')

        if login_required:
            return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)


        if request.method != 'POST':
            return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)



        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        to_user = get_admin_email()

        if not to_user:
            h.flash_error(_('Unable to send the issue report to the system admin.'))
            return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)

        issue_title = data_dict['issue_title'].strip()

        issue_description = h.render_markdown(data_dict['issue_description'])

        email_content = render('datagovmk/issue_email_template.html', extra_vars={
            'title': issue_title,
            'site_title': config.get('ckan.site_title', 'CKAN'),
            'description': issue_description,
            'date': datetime.now(),
            'username': c.userobj.fullname or c.userobj.name,
            'user': c.userobj,
            'user_url': h.url_for(controller='user', action='read', id=c.user, qualified=True)
        })

        subject = u'CKAN: Проблем | Problem | Issue: {title}'.format(title=issue_title)

        result = send_email(to_user['name'], to_user['email'], subject, email_content)

        if not result['success']:
            h.flash_error(result['message'])
        else:
            h.flash_success(toolkit._('The issue has been reported.'))
            extra_vars['successfuly_reported'] = True
        return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)


def get_admin_email():
    """Loads the admin email.

    If a system configuration is present, it is preffered to the CKAN sysadmins.
    The configuration property is ``ckanext.datagovmk.site_admin_email``.

    If no email is configured explicitly, then the email of the first CKAN
    sysadmin is used.

    :returns: ``str`` the email of the sysadmin to which to send emails with
        issues.

    """
    sysadmin_email = config.get('ckanext.datagovmk.site_admin_email', False)
    if sysadmin_email:
        name = sysadmin_email.split('@')[0]
        return {
            'email': sysadmin_email,
            'name': name
        }
    sysadmins = get_sysadmins()
    if sysadmins:
        return {
            'email': sysadmins[0].email,
            'name': sysadmins[0].fullname or sysadmins[0].name
        }
    return None


class StatsController(BaseController):

    def index(self):
        from ckanext.datagovmk import stats as stats_lib
        c = p.toolkit.c
        stats = stats_lib.Stats()
        rev_stats = stats_lib.RevisionStats()
        c.top_rated_packages = stats.top_rated_packages()
        c.most_edited_packages = stats.most_edited_packages()
        c.largest_groups = stats.largest_groups()
        c.top_tags = stats.top_tags()
        c.top_package_creators = stats.top_package_creators()
        c.new_packages_by_week = rev_stats.get_by_week('new_packages')
        c.deleted_packages_by_week = rev_stats.get_by_week('deleted_packages')
        c.num_packages_by_week = stats_lib.RevisionStats.get_num_packages_by_week()
        c.package_revisions_by_week = rev_stats.get_by_week('package_revisions')

        c.raw_packages_by_week = []
        for week_date, num_packages, cumulative_num_packages in c.num_packages_by_week:
            c.raw_packages_by_week.append({'date': h.date_str_to_datetime(week_date), 'total_packages': cumulative_num_packages})

        c.all_package_revisions = []
        c.raw_all_package_revisions = []
        for week_date, revs, num_revisions, cumulative_num_revisions in c.package_revisions_by_week:
            c.all_package_revisions.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_revisions))
            c.raw_all_package_revisions.append({'date': h.date_str_to_datetime(week_date), 'total_revisions': num_revisions})

        c.new_datasets = []
        c.raw_new_datasets = []
        for week_date, pkgs, num_packages, cumulative_num_packages in c.new_packages_by_week:
            c.new_datasets.append('[new Date(%s), %s]' % (week_date.replace('-', ','), num_packages))
            c.raw_new_datasets.append({'date': h.date_str_to_datetime(week_date), 'new_packages': num_packages})

        return p.toolkit.render('ckanext/stats/index.html')


class OverrideDatastoreController(DatastoreController):

    def dump(self, resource_id):
        try:
            offset = int_validator(request.GET.get('offset', 0), {})
        except toolkit.Invalid as e:
            toolkit.abort(400, u'offset: ' + e.error)
        try:
            limit = int_validator(request.GET.get('limit'), {})
        except toolkit.Invalid as e:
            toolkit.abort(400, u'limit: ' + e.error)
        bom = boolean_validator(request.GET.get('bom'), {})
        fmt = request.GET.get('format', 'csv')

        if fmt not in DUMP_FORMATS:
            toolkit.abort(400, _(
                u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

        try:
            dump_to(
                resource_id,
                response,
                fmt=fmt,
                offset=offset,
                limit=limit,
                options={u'bom': bom})
        except toolkit.ObjectNotFound:
            toolkit.abort(404, _('DataStore resource not found'))

def get_xml_element(element_name):
    '''Return element name according XML naming standards
    Capitalize every word and remove special characters
    :param element_name: xml element
    :type element_name: str
    :returns: Element name according XML standards
    :rtype: str
    '''
    clean_word = u''.join(c.strip(SPECIAL_CHARS) for c in element_name)
    if unicode(clean_word).isnumeric():
        return u'_' + unicode(element_name)
    first, rest = clean_word.split(u' ')[0], clean_word.split(u' ')[1:]
    return first + u''.join(w.capitalize()for w in rest)


def dump_to(resource_id, output, fmt, offset, limit, options):
    """ Overriden method """
    if fmt == 'csv':
        writer_factory = csv_writer
        records_format = 'csv'
    elif fmt == 'tsv':
        writer_factory = tsv_writer
        records_format = 'tsv'
    elif fmt == 'json':
        writer_factory = json_writer
        records_format = 'lists'
    elif fmt == 'xml':
        writer_factory = xml_writer
        records_format = 'objects'

    def start_writer(fields):
        bom = options.get(u'bom', False)
        return writer_factory(output, fields, resource_id, bom)

    def result_page(offs, lim):
        return toolkit.get_action('datastore_search')(None, {
            'resource_id': resource_id,
            'limit':
                PAGINATE_BY if limit is None
                else min(PAGINATE_BY, lim),
            'offset': offs,
            'sort': '_id',
            'records_format': records_format,
            'include_total': 'false',  # XXX: default() is broken
        })

    result = result_page(offset, limit)

    with start_writer(result['fields']) as wr:
        while True:
            if limit is not None and limit <= 0:
                break

            records = result['records']

            wr.write_records(records)

            if records_format == 'objects' or records_format == 'lists':
                if len(records) < PAGINATE_BY:
                    break
            elif not records:
                break

            offset += PAGINATE_BY
            if limit is not None:
                limit -= PAGINATE_BY
                if limit <= 0:
                    break

            result = result_page(offset, limit)


class XMLWriter(object):
    """ Overriden class """
    _key_attr = u'key'
    _value_tag = u'value'

    def __init__(self, response, columns):
        self.response = response
        self.id_col = columns[0] == u'_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def _insert_node(self, root, k, v, key_attr=None):
        element = SubElement(root, k)
        if v is None:
            element.attrib[u'xsi:nil'] = u'true'
        elif not isinstance(v, (list, dict)):
            element.text = text_type(v)
        else:
            if isinstance(v, list):
                it = enumerate(v)
            else:
                it = v.items()
            for key, value in it:
                self._insert_node(element, self._value_tag, value, key)

        if key_attr is not None:
            element.attrib[self._key_attr] = text_type(key_attr)

    def write_records(self, records):
        """ Overriden """
        for r in records:
            root = Element(u'row')
            if self.id_col:
                root.attrib[u'_id'] = text_type(r[u'_id'])
            for c in self.columns:
                node_name = get_xml_element(c)
                self._insert_node(root, node_name, r[c])
            ElementTree(root).write(self.response, encoding=u'utf-8')
            self.response.write(b'\n')


@contextmanager
def xml_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 XML data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (
            b'text/xml; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = (
                b'attachment; filename="{name}.xml"'.format(
                    name=encode_rfc2231(name)))
    if bom:
        response.write(BOM_UTF8)
    response.write(b'<data>\n')
    yield XMLWriter(response, [f['id'] for f in fields])
    response.write(b'</data>\n')


def extract_date(datestr):
    """ Change format of the date. Example: 01-08-2018 to 2018-08-01 00:00:00
    :param datestr: the date string which needs to be converted in different format
    :type datestr: str
    :returns: formatted string
    :rtype: str
    """
    datestr = datestr.strip() if datestr else ''
    m = re.match(r'(?P<mm>\d{1,2})(?P<sep>[-/])(?P<dd>\d{1,2})[-/](?P<yyyy>\d{4})', datestr)
    if m:
        if int(m.group('mm')) > 12:
            return _strptime('%m/%d/%Y' if m.group('sep') == '/' else '%m-%d-%Y', datestr)
        else:
            return _strptime('%d/%m/%Y' if m.group('sep') == '/' else '%d-%m-%Y', datestr)

    if re.match(r'\d{4}-\d{2}-\d{2}', datestr):
        return _strptime('%Y-%m-%d', datestr)

    return None

def _strptime(format_, datestr):
    try:
        return datetime.strptime(datestr, format_)
    except Exception as e:
        return None

def datetime_to_utc(dt):
    """Convert datetime to UTC
    :param dt: datetime
    :type dt: datetime
    :returns: converted datetime to UTC
    :rtype: datetime
    """
    return dt.replace(tzinfo=pytz.UTC)
