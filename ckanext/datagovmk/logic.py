from ckanext.datagovmk.schema import PRESETS
import ckanext.datagovmk.helpers as helpers
from ckanext.datagovmk.validators import create_schema
from ckan.logic.schema import default_create_package_schema


def _get_schema_override(data_dict, default_schema, direction="ingest"):
    schema = helpers.load_dataset_schema(data_dict, default_schema)

    for dsf in schema.get('dataset_fields', []):
        if not dsf.get('validators') and dsf.get('preset'):
            fldp = PRESETS.get(dsf['preset'])
            if fldp and fldp.get('validators'):
                dsf["validators"] = fldp['validators']

    create_schema(default_create_package_schema(), schema.get('dataset_fields', []), PRESETS, direction=direction)

def override_package_create(action_package_create, default_schema):
    def _package_create(context, data_dict):
        context['schema'] = _get_schema_override(data_dict, default_schema)
        return action_package_create(context, data_dict)

    return _package_create


def override_package_show(action_package_show, default_schema):
    
    def _package_show(context, data_dict):
        context['schema'] = _get_schema_override(data_dict, default_schema, direction="retrieve")
        pkg_data = action_package_show(context, data_dict)

        import json
        print json.dumps(pkg_data, indent=2)

        return pkg_data
    
    return _package_show
