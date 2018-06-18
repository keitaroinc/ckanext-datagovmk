import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.datagovmk.helpers as helpers


class DatagovmkPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

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
                helpers.get_groups
        }

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        validators = [ignore_missing, unicode]

        schema.update({
            'footer_links': validators,
        })

        return schema
