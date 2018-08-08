# -*- coding: utf-8 -*-

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
from io import StringIO

from ckan.controllers.package import PackageController
from ckan.controllers.user import UserController
from ckanext.datagovmk.model.stats import increment_downloads
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
from ckan.lib.base import BaseController, abort, render
from ckan.plugins import toolkit
from ckan.common import _, c, request, response, config
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

unflatten = dictization_functions.unflatten

log = getLogger(__name__)


SPECIAL_CHARS = u'#$%&!?\/@}{[]'


class DownloadController(PackageController):
    """Overrides CKAN's PackageController to add count for the resource downloads.
    """

    def resource_download(self, id, resource_id, filename=None):
        """Overrides CKAN's ``resource_download`` action. Adds counting of the
        number of downloads per resource and provides a direct download by downloading
        an uploaded file directly

        :param id: dataset id
        :type id: string

        :param resource_id: resource id
        :type resource_id: string
        """
        increment_downloads(resource_id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        try:
            rsc = get_action('resource_show')(context, {'id': resource_id})
            get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            abort(404, toolkit._('Resource not found'))

        if rsc.get('url_type') == 'upload':
            upload = uploader.get_resource_uploader(rsc)
            filepath = upload.get_path(rsc['id'])
            fileapp = paste.fileapp.FileApp(filepath)
            try:
                status, headers, app_iter = request.call_application(fileapp)
            except OSError:
                abort(404, toolkit._('Resource data not found'))
            response.headers.update(dict(headers))
            content_type, content_enc = mimetypes.guess_type(
                rsc.get('url', ''))
            if content_type:
                response.headers['Content-Type'] = content_type
            response.content_disposition = 'attachment; filename="%s"' % filename
            response.status = status
            return app_iter
        elif 'url' not in rsc:
            abort(404, toolkit._('No download is available'))
        h.redirect_to(rsc['url'])
    
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


class ApiController(BaseController):
    def i18n_js_translations(self, lang):
        ''' Patch for broken JS translations caused by Pylons to Flask
        migration. This method patches https://github.com/ckan/ckan/blob/master/ckan/views/api.py#L467

        :param lang: locale of the language
        :type lang: string

        :returns: the translated strings in a json file.

        :rtype: json

        '''

        ckan_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'ckan', 'ckan'
        )
        source = os.path.abspath(os.path.join(ckan_path, 'public',
                                 'base', 'i18n', '%s.js' % lang))
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
    u'''Return element name according XML naming standards
        Capitalize every word and remove special characters
       '''
    clean_word = u''.join(c.strip(SPECIAL_CHARS) for c in element_name)
    if unicode(clean_word).isnumeric():
        return u'_' + unicode(element_name)
    first, rest = clean_word.split(u' ')[0], clean_word.split(u' ')[1:]
    return first + u''.join(w.capitalize()for w in rest)


def dump_to(resource_id, output, fmt, offset, limit, options):
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