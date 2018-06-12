import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.datagovmk.helpers as helpers
import ckanext.datagovmk.loader as loader
import ckanext.datagovmk.validators as validators


class DatagovmkPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IValidators)

    _DEFAULT_DATASET_SCHEMA = {}

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datagovmk')

        DatagovmkPlugin._DEFAULT_DATASET_SCHEMA = loader.load_schema_module_path(config_.get('ckanext.datagovmk.dataset.schema', 
                                                                                             'ckanext.mk_dcatap:mk_dcatap_schema.json'))


    # ITemplateHelpers
    def get_helpers(self):
        return {
            'datagovmk_get_recently_updated_datasets':
                helpers.get_recently_updated_datasets,
            'datagovmk_get_most_active_organizations':
                helpers.get_most_active_organizations,
            'datagovmk_load_dataset_schema':
                helpers.new_load_dataset_schema_helper(DatagovmkPlugin._DEFAULT_DATASET_SCHEMA),
            'datagovmk_get_language_text':
                helpers.get_language_text,
            'datagovmk_field_type':
                helpers.get_form_field_type,
            'datagovmk_field_required':
                helpers.get_form_field_required,
            'datagovmk_get_preset':
                helpers.get_preset,
            'datagovmk_field_choices':
                helpers.get_field_choices
        }

    # IValidators
    def get_validators(self):
        return {
            'datagovmk_multiple_choice': validators.datagovmk_multiple_choice,
            'datagovmk_multiple_choice_output': validators.datagovmk_multiple_choice_output,
            'datagovmk_required': validators.datagovmk_required,
            'datagovmk_choices': validators.datagovmk_choices
        }