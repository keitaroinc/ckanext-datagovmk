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
                                     export_package_to_rdf)
from ckanext.datagovmk.lib import (verify_activation_link,
                                   create_activation_key)
from ckan.lib.base import BaseController, abort
from ckan.plugins import toolkit
from ckan.common import _, c, request, response
from ckan.lib.navl import dictization_functions

import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h
import ckan.lib.captcha as captcha

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
DataError = dictization_functions.DataError

get_action = logic.get_action

unflatten = dictization_functions.unflatten

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

    def datagovmk_register(self, data=None, errors=None, error_summary=None):
        return self.register(data, errors, error_summary)

    def perform_activation(self, id):
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
            h.flash_error(_('Unauthorized to edit user %') % id)
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
            user = get_action('datagovmk_user_create')(context, data_dict)
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

        h.flash_success(_('A confirmation email has been sent to "%s". Please '
                          'use the link in the email to continue.') %
                         data_dict['email'])
        if not c.user:
            # line below which logs the user in programatically is commented out
            # as we expect new accounts to be in the PENDING state by default.
            # set_repoze_user(data_dict['name'])
            if came_from:
                h.redirect_to(came_from)
            else:
                # h.redirect_to(controller='user', action='me')
                ## instead of redirected above, redirect to the login page=
                h.redirect_to(controller='user', action='login')
        else:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(_('User "%s" is now registered but you are still '
                            'logged in as "%s" from before') %
                            (data_dict['name'], c.user))
            if authz.is_sysadmin(c.user):
                # the sysadmin created a new user. We redirect him to the
                # activity page for the newly created user
                h.redirect_to(controller='user',
                                action='activity',
                                id=data_dict['name'])
            else:
                return render('user/logout_first.html')



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
