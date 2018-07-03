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
from ckanext.datagovmk.model.stats import increment_downloads
from ckanext.datagovmk.helpers import get_storage_path_for
from ckan.lib.base import BaseController, abort
from ckan.plugins import toolkit
from ckan.common import c, request, response

import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h

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
        """
        increment_downloads(resource_id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        try:
            rsc = get_action('resource_show')(context, {'id': resource_id})
            get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        if rsc.get('url_type') == 'upload':
            upload = uploader.get_resource_uploader(rsc)
            filepath = upload.get_path(rsc['id'])
            fileapp = paste.fileapp.FileApp(filepath)
            try:
                status, headers, app_iter = request.call_application(fileapp)
            except OSError:
                abort(404, _('Resource data not found'))
            response.headers.update(dict(headers))
            content_type, content_enc = mimetypes.guess_type(
                rsc.get('url', ''))
            if content_type:
                response.headers['Content-Type'] = content_type
            response.content_disposition = 'attachment; filename="%s"' % filename
            response.status = status
            return app_iter
        elif 'url' not in rsc:
            abort(404, _('No download is available'))
        h.redirect_to(rsc['url'])


class ApiController(BaseController):
    def i18n_js_translations(self, lang):
        ''' Patch for broken JS translations caused by Pylons to Flask
        migration. This method patches https://github.com/ckan/ckan/blob/master/ckan/views/api.py#L467 '''
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

    def download_resources_metadata(self, package_id):
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
        

    

def _export_resources_json(zip_file, pkg_dict, request, response):
    for resource in pkg_dict['resources']:
        rc_filename = '%s.json' % resource.get('name') or resource['id']
        zip_file.writestr(rc_filename, json.dumps(resource))


def _export_to_rdf(zip_file, pkg_dict, request, response, file_ext='rdf'):
    from ckanext.dcat.processors import RDFSerializer
    serializer = RDFSerializer()

    file_name = '%s.%s' % (pkg_dict.get('name') or pkg_dict['id'], file_ext)

    output = serializer.serialize_dataset(pkg_dict,
                                          _format='xml')
    
    zip_file.writestr(file_name, output)


def _export_resources_rdf(zip_file, pkg_dict, request, response):
    return _export_to_rdf(zip_file, pkg_dict, request, response, 'rdf')


def _export_resources_xml(zip_file, pkg_dict, request, response):
    # It only makes sense to export in RDF valid XML, containing the dataset info as well.
    return _export_to_rdf(zip_file, pkg_dict, request, response, 'rdf')


def _export_resources_csv(zip_file, pkg_dict, request, response):
    for resource in pkg_dict['resources']:
        rc_filename = '%s.json' % resource.get('name') or resource['id']
        fieldnames = [prop for prop,_ in resource.iteritems()]
        output = StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        print fieldnames
        print resource
        writer.writeheader()
        
        writer.writerow(resource)

        zip_file.writestr(rc_filename, output.getvalue()) 

_SUPPORTED_EXPORTS = {
    'json': _export_resources_json,
    'rdf': _export_resources_rdf,
    'xml': _export_resources_xml,
    'csv': _export_resources_csv
}

def _open_temp_zipfile():
    file_name = uuid.uuid4().hex + '.{ext}'.format(ext='zip')
    file_path = get_storage_path_for('temp-datagovmk') + '/' + file_name

    return zipfile.ZipFile(file_path, 'w')
