import uuid
import os
import json
from zipfile import ZipFile

from flask import Blueprint, make_response, send_file
from logging import getLogger


from ckan.plugins import toolkit
from ckan.plugins.toolkit import c, request
from ckan import model
import ckan.lib.helpers as h

from ckanext.datagovmk.helpers import get_storage_path_for
from ckanext.datagovmk.utils import (export_resource_to_rdf,
                                     export_resource_to_xml,
                                     export_dict_to_csv,
                                     to_utf8_str,
                                     export_package_to_xml,
                                     export_package_to_rdf)


log = getLogger(__name__)

bulk_download = Blueprint('bulk_download', __name__)
"""Download metadata as ZIP file."""


def download_resources_metadata(package_id):
    """Download resources metadata in different formats as ZIP file.

    :param str package_id: the id of the package containing the resources.

    """
    context = {'model': model, 'session': model.Session,
               'user': c.user, 'auth_user_obj': c.userobj}

    pkg_dict = toolkit.get_action('package_show')(context, {'id': package_id})

    resources = request.args.get('resources')
    if resources and resources.lower() != 'all':
        resources = [r.strip() for r in resources.split(',')]
    else:
        resources = None

    tmp_file_path = None

    try:
        with ZipFile(_open_temp_zipfile(), 'w') as zipf:
            tmp_file_path = zipf.filename
            _export_resources(zipf, pkg_dict, resources)
    except Exception as exc:
        log.error('Error while preparing zip archive: %s', exc)
        log.exception(exc)
        raise exc
    try:
        zip_file_name = '%s_resources.zip' % pkg_dict['name']

        return send_file(tmp_file_path,
                         mimetype='application/zip',
                         as_attachment=True,
                         attachment_filename=zip_file_name)

    finally:
        os.remove(tmp_file_path)


def _export_resources(zip_file, pkg_dict, resources):
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

    exporter(zip_file, pkg_dict)


def download_package_metadata(package_id):
    """Download package metadata in one of the supported formats.

    :param string package_id: the id of the package

    """
    response = make_response()
    context = {'model': model, 'session': model.Session,
               'user': c.user, 'auth_user_obj': c.userobj}

    package_dict = toolkit.get_action('package_show')(
                                      context, {'id': package_id})
    _format = request.args.get('format', 'json')
    export_def = _SUPPORTED_PACKAGE_EXPORTS.get(_format)
    if not export_def:
        raise Exception('Unsupported export format: %s' % _format)

    content_type = export_def['content-type']
    response.headers['Content-Type'] = content_type

    exporter = export_def['exporter']

    file_name = '%s.%s' % (package_dict.get('name') or
                           package_dict['id'], _format)

    response.headers['Content-disposition'] = \
        'attachment; filename=' + file_name
    response.charset = 'UTF-8'

    exporter(package_dict, request, response)

    return response


def _open_temp_zipfile():
    file_name = uuid.uuid4().hex + '.{ext}'.format(ext='zip')
    file_path = get_storage_path_for('temp-datagovmk') + '/' + file_name
    return file_path


def _export_resources_json(zip_file, pkg_dict):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        rc_filename = str('%s.json' % resource_name)
        data = str(json.dumps(resource, indent=4, ensure_ascii=False))
        zip_file.writestr(rc_filename, data)


def _export_to_rdf(zip_file, pkg_dict, file_ext='rdf'):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        file_name = u'%s.rdf' % resource_name

        output = export_resource_to_rdf(resource, pkg_dict)
        zip_file.writestr(file_name, output)


def _export_resources_rdf(zip_file, pkg_dict):
    return _export_to_rdf(zip_file, pkg_dict, 'rdf')


def _export_resources_xml(zip_file, pkg_dict):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True
        file_name = u'%s.xml' % resource_name
        output = export_resource_to_xml(resource)
        zip_file.writestr(file_name, output)


def _export_resources_csv(zip_file, pkg_dict):
    file_names = {}
    for resource in pkg_dict['resources']:
        resource_name = h.resource_display_name(resource)
        if file_names.get(resource_name):
            resource_name = u'%s_%s' % (resource_name, resource['id'])
        else:
            file_names[resource_name] = True

        rc_filename = to_utf8_str('%s.csv' % resource_name)
        output = export_dict_to_csv(resource)

        zip_file.writestr(rc_filename, output)


_SUPPORTED_EXPORTS = {
    'json': _export_resources_json,
    'rdf': _export_resources_rdf,
    'xml': _export_resources_xml,
    'csv': _export_resources_csv
}


def _export_package_json(package_dict, request, response):
    json.dump(package_dict, response.stream, indent=4, ensure_ascii=False)


def _export_package_xml(package_dict, request, response):
    response.stream.write(export_package_to_xml(package_dict))


def _export_package_to_rdf(package_dict, request, response):
    response.stream.write(export_package_to_rdf(package_dict, _format='xml'))


def _export_package_to_csv(package_dict, request, response):
    result = {}
    for key, value in package_dict.items():
        if isinstance(value, list):
            if not value:
                value = ""
            elif len(value) == 1:
                value = value[0]
        result[key] = value

    if result.get('organization'):
        result['organization'] = \
            result['organization'].get('name') or result['organization']['id']

    if result.get('tags'):
        tags = []
        for tag in result['tags']:
            tags.append(tag.get('name') or tag['id'])
        result['tags'] = ','.join(tags)

    response.stream.write(export_dict_to_csv(result))


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


bulk_download.add_url_rule('/api/download/<package_id>/resources',
                           view_func=download_resources_metadata,
                           methods=['GET', 'POST'])
bulk_download.add_url_rule('/api/download/<package_id>/metadata',
                           view_func=download_package_metadata,
                           methods=['GET', 'POST'])
