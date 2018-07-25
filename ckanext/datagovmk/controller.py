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
from ckanext.datagovmk.model.stats import increment_downloads
from ckanext.datagovmk.helpers import get_storage_path_for
from ckanext.datagovmk.utils import (export_resource_to_rdf,
                                     export_resource_to_xml,
                                     export_dict_to_csv,
                                     to_utf8_str,
                                     export_package_to_xml,
                                     export_package_to_rdf,
                                     send_email)
from ckan.lib.base import BaseController, abort, render
from ckan.plugins import toolkit
from ckan.common import c, request, response, config

import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h
from ckan.controllers.admin import get_sysadmins
import bleach
from datetime import datetime

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
get_action = logic.get_action
log = getLogger(__name__)


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

        :param dict package_dict: the package metadata.

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



def _export_resources_json(zip_file, pkg_dict, request, response):
    for resource in pkg_dict['resources']:
        rc_filename = '%s.json' % resource.get('name') or resource['id']
        zip_file.writestr(rc_filename, json.dumps(resource))


def _export_to_rdf(zip_file, pkg_dict, request, response, file_ext='rdf'):
    for resource in pkg_dict['resources']:
        file_name = '%s.rdf' % resource.get('name') or resource['id']
        output = export_resource_to_rdf(resource, pkg_dict)
        zip_file.writestr(file_name, output)



def _export_resources_rdf(zip_file, pkg_dict, request, response):
    return _export_to_rdf(zip_file, pkg_dict, request, response, 'rdf')


def _export_resources_xml(zip_file, pkg_dict, request, response):
    for resource in pkg_dict['resources']:
        file_name = '%s.xml' % resource.get('name') or resource['id']
        output = export_resource_to_xml(resource)
        zip_file.writestr(file_name.encode('utf-8'), output.encode('utf-8'))


def _export_resources_csv(zip_file, pkg_dict, request, response):
    for resource in pkg_dict['resources']:
        rc_filename =to_utf8_str('%s.csv' % resource.get('name') or resource['id'])
        output = export_dict_to_csv(resource)
        zip_file.writestr(rc_filename, output)

_SUPPORTED_EXPORTS = {
    'json': _export_resources_json,
    'rdf': _export_resources_rdf,
    'xml': _export_resources_xml,
    'csv': _export_resources_csv
}


def _export_package_json(package_dict, request, response):
    json.dump(package_dict, response, indent=4)


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

        to_email = get_admin_email()

        if not to_email:
            h.flash_error(_('Unable to send the issue report to the system admin.'))
            return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)
        
        from_email = c.userobj.email

        issue_title = data_dict['issue_title'].strip()

        issue_description = h.render_markdown(data_dict['issue_description'])

        email_content = render('datagovmk/issue_email_template.html', extra_vars={
            'title': issue_title,
            'description': issue_description,
            'date': datetime.now(),
            'username': c.userobj.fullname or c.userobj.name
        })

        subject = toolkit._('Issue: {title}').format(title=issue_title)
        
        result = send_email(from_email, to_email, subject, email_content)
        
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
        return sysadmin_email
    sysadmins = get_sysadmins()
    if sysadmins:
        return sysadmins[0].email
    return None