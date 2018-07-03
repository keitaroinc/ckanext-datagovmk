import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.datagovmk.helpers as helpers
from ckan.lib.plugins import DefaultTranslation
from ckan.logic import get_action
from routes.mapper import SubMapper
from ckanext.datagovmk import actions
from ckanext.datagovmk import auth


class DatagovmkPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datagovmk')

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'datagovmk_get_recently_updated_datasets':
                helpers.get_recently_updated_datasets,
            'datagovmk_get_most_active_organizations':
                helpers.get_most_active_organizations,
            'datagovmk_get_groups':
                helpers.get_groups,
            'datagovmk_get_dataset_stats':
                helpers.get_dataset_stats,
            'datagovmk_get_resource_stats':
                helpers.get_resource_stats,
            'datagovmk_total_downloads':
                helpers.get_total_package_downloads,
            'datagovmk_get_related_datasets':
                helpers.get_related_datasets
        }

    # IActions

    def get_actions(self):
        return {
            'datagovmk_get_related_datasets': actions.get_related_datasets,
            'datagovmk_prepare_zip_resources': actions.prepare_zip_resources,
            'datagovmk_download_zip': actions.download_zip,
            'datagovmk_download_dataset_metadata': actions.download_dataset_metadata,
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'datagovmk_get_related_datasets': auth.get_related_datasets,
            'datagovmk_get_groups': helpers.get_groups
        }

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        validators = [ignore_missing, unicode]

        schema.update({
            'footer_links': validators,
        })

        return schema

    # IRoutes
    def before_map(self, map):
        map.connect(
            '/api/i18n/{lang}',
            controller='ckanext.datagovmk.controller:ApiController',
            action='i18n_js_translations'
        )
        with SubMapper(map, controller='ckanext.datagovmk.controller:DownloadController') as m:
            # Override the resource download links, so we can count the number of downloads.
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download',
                      action='resource_download')
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download/{filename}',
                      action='resource_download')

        map.connect('/api/download/{package_id}/resources',
                    controller='ckanext.datagovmk.controller:BulkDownloadController',
                    action='download_resources_metadata')

        return map
