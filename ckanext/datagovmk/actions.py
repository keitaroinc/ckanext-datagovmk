import os
import uuid
import requests
import zipfile
import hashlib
import subprocess

from ckan.plugins import toolkit
from ckan.controllers.admin import get_sysadmins
from ckanext.datagovmk import helpers as h
from ckanext.datagovmk import logic as l
from logging import getLogger
from ckanext.dcat.processors import RDFSerializer
from ckan.common import config

import ckan.logic as logic
import ckan.plugins as plugins
import ckan.lib.uploader as uploader

log = getLogger(__name__)

_ = toolkit._
ValidationError = toolkit.ValidationError
get_action = toolkit.get_action
get_or_bust = toolkit.get_or_bust
check_access = toolkit.check_access
NotFound = logic.NotFound

SUPPORTED_RESOURCE_MIMETYPES = [
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'application/x-msdownload',
    'application/msword',
    'application/vnd.google-earth.kml+xml',
    'application/vnd.ms-excel',
    'application/msexcel',
    'application/x-msexcel',
    'application/x-ms-excel',
    'application/x-excel',
    'application/x-dos_ms_excel',
    'application/xls',
    'application/x-xls',
    'wcs',
    'application/x-javascript',
    'application/x-msaccess',
    'application/netcdf',
    'text/tab-separated-values',
    'text/x-perl',
    'application/vnd.google-earth.kmz+xml',
    'application/vnd.google-earth.kmz',
    'application/owl+xml',
    'application/x-n3',
    'application/zip',
    'application/gzip',
    'application/x-gzip',
    'application/x-qgis',
    'application/vnd.oasis.opendocument.spreadsheet',
    'application/vnd.oasis.opendocument.text',
    'application/json',
    'image/x-ms-bmp',
    'application/rar',
    'image/tiff',
    'application/vnd.oasis.opendocument.database',
    'text/plain',
    'application/x-director',
    'application/vnd.oasis.opendocument.formula',
    'application/vnd.oasis.opendocument.graphics',
    'application/xml',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'application/octet-stream',
    'application/xslt+xml',
    'image/svg+xml',
    'application/vnd.ms-powerpoint',
    'application/vnd.oasis.opendocument.presentation',
    'image/jpeg',
    'application/sparql-results+xml',
    'image/gif',
    'application/rdf+xml',
    'application/pdf',
    'text/csv',
    'application/vnd.oasis.opendocument.chart',
    'application/atom+xml',
    'application/x-tar',
    'image/png',
    'application/rss+xml',
    'application/geo+json'
]


@toolkit.side_effect_free
def get_related_datasets(context, data_dict):

    '''This is an action function which returns related datasets for a single dataset, based
    on groups and tags which are parts of the dataset itself.

    :param id: id od the single dataset for which we would like to return
        the related datasets
    :type id: string

    :param limit: Limit of the datasets to be returned, default is 3
    :type limit: integer

    :returns: a list of datasets which are related with the one we have chosen
    :rtype: list

    '''

    id = data_dict.get('id')
    limit = int(data_dict.get('limit', 3))
    related_datasets = []
    related_datasets_ids = []

    if id is None:
        raise ValidationError(_('Missing dataset id'))

    dataset = get_action('package_show')(data_dict={'id': id})

    groups = dataset.get('groups')
    tags = dataset.get('tags')

    for group in groups:
        data_dict = {
            'id': group.get('id'),
            'include_datasets': True
        }
        group_dict = get_action('group_show')(data_dict=data_dict)

        group_datasets = group_dict.get('packages')

        for group_dataset in group_datasets:
            group_dataset_id = group_dataset.get('id')
            if group_dataset_id != dataset.get('id') and \
               group_dataset_id not in related_datasets_ids:
                related_datasets.append(group_dataset)
                related_datasets_ids.append(group_dataset_id)

    for tag in tags:
        data_dict = {
            'id': tag.get('id'),
            'include_datasets': True
        }
        tag_dict = get_action('tag_show')(data_dict=data_dict)

        tag_datasets = tag_dict.get('packages')

        for tag_dataset in tag_datasets:
            tag_dataset_id = tag_dataset.get('id')
            if tag_dataset_id != dataset.get('id') and \
               tag_dataset_id not in related_datasets_ids:
                related_datasets.append(tag_dataset)
                related_datasets_ids.append(tag_dataset_id)

    return related_datasets[:limit]


@toolkit.side_effect_free
def prepare_zip_resources(context, data_dict):
    """Creates zip archive and stores it under CKAN's storage path.

    :param resources: a list of ids of the resources
    :type resources: list

    :return: a dictionary containing the zip_id of the created archive
    :rtype: dict
    """
    file_name = uuid.uuid4().hex + '.{ext}'.format(ext='zip')
    file_path = h.get_storage_path_for('temp-datagovmk') + '/' + file_name
    resourceArchived = False
    package_id = None

    try:
        resource_ids = data_dict.get('resources')
        with zipfile.ZipFile(file_path, 'w') as zip:
            for resource_id in resource_ids:
                data_dict = {'id': resource_id}
                resource = toolkit.get_action('resource_show')({}, data_dict)

                url = resource.get('url')
                if resource['url_type'] == 'upload':
                    name = url.split('/')[-1]
                else:
                    name = resource['name']
                    if os.path.splitext(name)[-1] == '':
                        _format = resource['format']
                        if _format:
                            name += '.{ext}'.format(ext=_format.lower())

                if package_id is None:
                    package_id = resource['package_id']

                headers = {'Authorization': get_sysadmins()[0].apikey}
                try:
                    r = requests.get(url, headers=headers)
                except Exception:
                    continue

                content_type = r.headers['Content-Type'].split(';')[0]

                if content_type in SUPPORTED_RESOURCE_MIMETYPES:
                    resourceArchived = True
                    zip.writestr(name, r.content)
    except Exception, ex:
        log.error('An error occured while preparing zip archive. Error: %s' % ex)
        raise

    zip_id = file_name
    try:
        package = toolkit.get_action('package_show')({}, {'id': package_id})
        package_name = package['name']

        zip_id += '::{name}'.format(name=package_name)
    except:
        pass

    if resourceArchived:
        return {'zip_id': zip_id}

    os.remove(file_path)

    return {'zip_id': None}


@toolkit.side_effect_free
def download_zip(context, data_dict):
    """Downloads a zip file

    :param id: an id of the created zip archive, format: filename::packagename
    :type id: string
    """
    file_name, package_name = data_dict.get('id').split('::')
    file_path = h.get_storage_path_for('temp-datagovmk/' + file_name)

    if not package_name:
        package_name = 'resources'
    package_name += '.zip'

    with open(file_path, 'r') as f:
        toolkit.response.write(f.read())

    toolkit.response.content_disposition = 'attachment; filename=' + package_name
    os.remove(file_path)


def safe_override(action):
    """Decorator for save override of standard CKAN actions.
    When overriding CKAN actions you must be aware of the extensions
    order and whether some other extension have already registered the action.

    When decorated with this decorator, you can provide a chained implementation
    for the given action withour checking if there are prior extensions or just
    the CKAN core action.

    Your action will be called with the previous (the original) action as a first argument.

    Usage:

    .. code-block:: python

        import ckan.plugins as plugins
        from ckan.logic import get_action


        @safe_override
        def package_create_override(package_create, context, data_dict):
            # add extra logic here

            # then pass the control to the original action
            return package_create(context, data_dict)


        class MyPlugin(plugins.SingletonPlugin):
            plugins.implements(plugins.IActions)

            def get_actions(self):
                prev_package_create = get_action('package_create')

                return {
                    'package_create': package_create_override(prev_package_create)
                }

    :param function action: the override function for the CKAN core action.

    :returns: a wrapper accepting the original action to be chained.
    :rtype: function

    """
    def get_safe_override(original_action):
        def _action(*args, **kwargs):
            return action(original_action, *args, **kwargs)
        return _action
    return get_safe_override


@safe_override
def add_spatial_data(package_action, context, data_dict):
    """Override for ``package_create`` and ``package_update`` that
    adds/updates the spatial data.

    :param function package_action: the previous (original) action (either ``package_create`` or
        ``package_update``).
    :param context: CKAN actions context.
    :param dict data_dict: the package data dict.

    :returns: the CKAN ``package_create``/``package_update`` result.
    :rtype: dict

    """
    try:
        l.import_spatial_data(data_dict)
    except Exception as e:
        log.warning(e)
    return package_action(context, data_dict)


def resource_create(context, data_dict):
    '''Overrides CKAN's ``resource_create`` action. Calculates checksum of
    the file and if file exists it will notify the user.
    '''

    model = context['model']

    package_id = get_or_bust(data_dict, 'package_id')
    if not data_dict.get('url'):
        data_dict['url'] = ''

    pkg_dict = get_action('package_show')(
        dict(context, return_type='dict'),
        {'id': package_id})

    check_access('resource_create', context, data_dict)

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_create(context, data_dict)

    if 'resources' not in pkg_dict:
        pkg_dict['resources'] = []

    upload = uploader.get_resource_uploader(data_dict)

    if hasattr(upload, 'upload_file'):
        # Checksum calculated for resource file must be different from checksum calculaated
        # by Datapushes that's why '-resource' string is added to the checksum
        checksum = '%s-%s' % (_calculate_checksum(upload.upload_file), 'resource')

        rsc = model.Session.query(model.Resource).\
            filter_by(package_id=pkg_dict['id'], hash=checksum, state='active').\
            first()
        if rsc:
            raise ValidationError({_('message'): [_('Resource already exists')]})
        else:
            data_dict['hash'] = checksum
    elif data_dict.get('url'):
        _validate_link(data_dict.get('url'))
    else:
        raise ValidationError({_('message'): [_('Resource file is missing')]})


    if 'mimetype' not in data_dict:
        if hasattr(upload, 'mimetype'):
            data_dict['mimetype'] = upload.mimetype

    if 'size' not in data_dict:
        if hasattr(upload, 'filesize'):
            data_dict['size'] = upload.filesize

    pkg_dict['resources'].append(data_dict)

    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except ValidationError as e:
        try:
            raise ValidationError(e.error_dict['resources'][-1])
        except (KeyError, IndexError):
            raise ValidationError(e.error_dict)

    # Get out resource_id resource from model as it will not appear in
    # package_show until after commit
    upload.upload(context['package'].resources[-1].id,
                  uploader.get_max_resource_size())

    model.repo.commit()

    #  Run package show again to get out actual last_resource
    updated_pkg_dict = get_action('package_show')(context, {'id': package_id})
    resource = updated_pkg_dict['resources'][-1]

    #  Add the default views to the new resource
    get_action('resource_create_default_resource_views')(
        {'model': context['model'],
         'user': context['user'],
         'ignore_auth': True
         },
        {'resource': resource,
         'package': updated_pkg_dict
         })

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_create(context, resource)

    return resource


def resource_update(context, data_dict):
    '''Update a resource.

    To update a resource you must be authorized to update the dataset that the
    resource belongs to.

    For further parameters see
    :py:func:`~ckan.logic.action.create.resource_create`.

    :param id: the id of the resource to update
    :type id: string

    :returns: the updated resource
    :rtype: string

    '''
    model = context['model']
    user = context['user']
    id = get_or_bust(data_dict, "id")

    if not data_dict.get('url'):
        data_dict['url'] = ''

    resource = model.Resource.get(id)
    context["resource"] = resource
    old_resource_format = resource.format

    if not resource:
        log.debug('Could not find resource %s', id)
        raise NotFound(_('Resource was not found.'))

    check_access('resource_update', context, data_dict)
    del context["resource"]

    package_id = resource.package.id
    pkg_dict = get_action('package_show')(dict(context, return_type='dict'),
                                           {'id': package_id})

    for n, p in enumerate(pkg_dict['resources']):
        if p['id'] == id:
            break
    else:
        log.error('Could not find resource %s after all', id)
        raise NotFound(_('Resource was not found.'))

    # Persist the datastore_active extra if already present and not provided
    if ('datastore_active' in resource.extras and
            'datastore_active' not in data_dict):
        data_dict['datastore_active'] = resource.extras['datastore_active']

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.before_update(context, pkg_dict['resources'][n], data_dict)

    upload = uploader.get_resource_uploader(data_dict)

    if hasattr(upload, 'upload_file'):
        # Checksum calculated for resource file must be different from checksum calculaated
        # by Datapushes that's why '-resource' string is added to the checksum
        checksum = '%s-%s' % (_calculate_checksum(upload.upload_file), 'resource')

        rsc = model.Session.query(model.Resource).\
            filter_by(package_id=pkg_dict['id'], hash=checksum, state='active').\
            first()
        if rsc:
            raise ValidationError(
                {_('message'): [_('Resource already exists')]})
        else:
            data_dict['hash'] = checksum
    elif data_dict.get('url'):
        _validate_link(data_dict.get('url'))
    else:
        raise ValidationError({_('message'): [_('Resource file is missing')]})

    if 'mimetype' not in data_dict:
        if hasattr(upload, 'mimetype'):
            data_dict['mimetype'] = upload.mimetype

    if 'size' not in data_dict and 'url_type' in data_dict:
        if hasattr(upload, 'filesize'):
            data_dict['size'] = upload.filesize

    pkg_dict['resources'][n] = data_dict

    try:
        context['defer_commit'] = True
        context['use_cache'] = False
        updated_pkg_dict = get_action('package_update')(context, pkg_dict)
        context.pop('defer_commit')
    except ValidationError as e:
        try:
            raise ValidationError(e.error_dict['resources'][-1])
        except (KeyError, IndexError):
            raise ValidationError(e.error_dict)

    upload.upload(id, uploader.get_max_resource_size())
    model.repo.commit()

    resource = get_action('resource_show')(context, {'id': id})

    if old_resource_format != resource['format']:
        get_action('resource_create_default_resource_views')(
            {'model': context['model'], 'user': context['user'],
             'ignore_auth': True},
            {'package': updated_pkg_dict,
             'resource': resource})

    for plugin in plugins.PluginImplementations(plugins.IResourceController):
        plugin.after_update(context, resource)

    return resource


def _calculate_checksum(file):
    hash_md5 = hashlib.md5()
    for chunk in iter(lambda: file.read(4096), b""):
        hash_md5.update(chunk)

    return hash_md5.hexdigest()

def _validate_link(link):
    # HTTP status code meaning:
    # 1xx - informational
    # 2xx - success
    # 3xx - redirection
    # 4xx - client error
    # 5xx - server error
    try:
        response = requests.head(link)
    except Exception:
        raise ValidationError({_('message'): [_('Invalid URL')]})

    if int(response.status_code) >= 400:
        raise ValidationError({_('message'): [_('Invalid URL')]})


def start_script(context, data_dict):
    """ This action is only intended to be used for starting scripts as cron
    jobs on the server. It's only available for system administrators.

    Scripts are located at `ckanext-datagovmk/scripts/cron_jobs`.

    :param name: The name of the script to be executed. Available script name
    is the name of the file of the script located at
    `ckanext-datagovmk/scripts/cron_jobs`. For example `archiver`.
    :type name: string

    :returns: Message that the script has been successfully executed. Since
    the script is executed as a subprocess, if there is an error it is not
    caught in the process where CKAN is started.
    :rtype: string
    """

    check_access('datagovmk_start_script', context, data_dict)

    name = get_or_bust(data_dict, 'name')
    cron_jobs_dir = os.path.join(
        os.path.dirname(__file__), '..', '..', 'scripts', 'cron_jobs'
    )
    available_script_names = [os.path.splitext(filename)[0]
                              for filename in os.listdir(cron_jobs_dir)]

    if name not in available_script_names:
        raise ValidationError({
            'name': _('No script was found for the provided name')
        })

    script_location = os.path.join(cron_jobs_dir, '{0}.sh'.format(name))
    config_file_location = config['__file__']

    subprocess.call(['/bin/sh', script_location, config_file_location])

    return 'Script was successfully executed.'
