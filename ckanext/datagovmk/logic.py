from ckanext.datagovmk.schema import PRESETS
import ckanext.datagovmk.helpers as helpers
from ckanext.datagovmk.validators import create_schema
from ckan.logic.schema import default_create_package_schema


def _get_schema_override(data_dict, default_schema, action="create"):
    schema = helpers.load_dataset_schema(data_dict, default_schema)
    print 'Schema -> ', schema is not None
    for dsf in schema.get('dataset_fields', []):
        if not dsf.get('validators') and dsf.get('preset'):
            fldp = PRESETS.get(dsf['preset'])
            if fldp and fldp.get('validators'):
                dsf["validators"] = fldp['validators']

    return create_schema(default_create_package_schema(), schema.get('dataset_fields', []), PRESETS, action=action)

def override_package_create(action_package_create, default_schema):
    def _package_create(context, data_dict):
        context['schema'] = _get_schema_override(data_dict, default_schema, 'create')
        print 'Context has schema: ', context['schema'] is not None, type(context['schema'])
        return action_package_create(context, data_dict)

    return _package_create


def override_package_show(action_package_show, default_schema):
    
    def _package_show(context, data_dict):
        context['schema'] = _get_schema_override(data_dict, default_schema, "show")
        pkg_data = action_package_show(context, data_dict)
        return pkg_data
    
    return _package_show

def override_package_update(action_package_update, default_schema):
    def _package_update(context, data_dict):
         context['schema'] = _get_schema_override(data_dict, default_schema, "update")
         return action_package_update(context, data_dict)
    return _package_update
