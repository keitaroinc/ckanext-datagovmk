from ckan.plugins import toolkit
from ckan.lib import search
from ckan.lib.i18n import get_lang
from datetime import datetime
import ckanext.datagovmk.loader as loader
from ckan.common import config, request
from jinja2.runtime import Undefined
from ckanext.datagovmk.schema import PRESETS

def _get_action(action, context_dict, data_dict):
    return toolkit.get_action(action)(context_dict, data_dict)

def get_recently_updated_datasets(limit=5):
    '''
     Returns recent created or updated datasets.

    :param limit: Limit of the datasets to be returned
    :return: list
    '''
    try:
        pkg_search_results = toolkit.get_action('package_search')(data_dict={
            'sort': 'metadata_modified desc',
            'rows': limit,
        })['results']

    except toolkit.ValidationError, search.SearchError:
        return []
    else:
        pkgs = []
        for pkg in pkg_search_results:
            package = toolkit.get_action('package_show')(
                data_dict={'id': pkg['id']})
            if package.get('metadata_modified'):
                modified = datetime.strptime(
                    package['metadata_modified'].split('T')[0], '%Y-%m-%d')
                package['days_ago_modified'] = ((datetime.now() - modified).days)
                pkgs.append(package)
            else:
                print "package invalid ===> ", package['name']
        return pkgs

def get_most_active_organizations(limit=5):
    '''
    Returns most active organizations by number of datasets published

    :param limit: Number of organizations to be returned
    :return list
    '''
    organizatons = toolkit.get_action('organization_list')(data_dict={
        'all_fields': True,
        'order_by': 'packages',
        'limit': limit
    })
    return organizatons


def load_dataset_schema(data_dict, default_schema):
    # check in extras, if specific dataset schema was set
    for extra in data_dict.get('extras', []):
        if extra['key'] == 'dataset_schema':
            print ' ==> Loading dataset_schema: ', extra['value']
            try:
                return loader.load_schema_module_path(extra['value'])
            except:
                return default_schema
    print 'Loading default schema: ', default_schema is not None, str(type(default_schema))
    return default_schema


def new_load_dataset_schema_helper(default_schema):
    def _load_dataset_schema(data_dict):
        return load_dataset_schema(data_dict, default_schema)
    return _load_dataset_schema


def get_language_text(text):
    if text is None:
        return u''
    
    if isinstance(text, basestring):
        return text
    if isinstance(text, Undefined):
       return u''

    assert isinstance(text, dict)
    lang_code = get_lang()
    lang_text = text.get(lang_code)
    
    if lang_text is None:
        lang_code = config.get('ckan.locale_default', 'en')
        lang_text = text.get(lang_code)
        if not lang_code:
            _, v = sorted(text.items())[0]
            lang_text = v
    return lang_text


def get_form_field_type(field):
    form_snippet = ''
    if field:
        form_snippet = field.get('form_snippet')
    if form_snippet == 'markdown.html':
        return 'markdown'
    else:
        return 'text'


def get_form_field_required(field):
    if 'required' in field:
        return field['required']
    return 'not_empty' in field.get('validators', '').split()


def get_preset(field):
    if field.get('preset'):
        return PRESETS.get(field['preset'])
    return PRESETS.get('_generic_field')


def get_field_choices(field):
    """
    :param field: scheming field definition
    :returns: choices iterable or None if not found.
    """
    if 'choices' in field:
        return field['choices']
    if 'choices_helper' in field:
        from ckantoolkit import h
        choices_fn = getattr(h, field['choices_helper'])
        return choices_fn(field)


def has_query_param(param):
    # Checks if the provided parameter is part of the current URL query params

    params = dict(request.params)

    if param in params:
        return True

    return False


def get_choices_label(choices, value):
    """
    :param choices: choices list of {"label": .., "value": ..} dicts
    :param value: value selected

    Return the label from choices with a matching value, or
    the value passed when not found. Result is passed through
    get_language_text before being returned.
    """
    for c in choices:
        if c['value'] == value:
            return get_language_text(c.get('label', value))
    return get_language_text(value)


def get_groups():
    # Helper used on the homepage for showing groups

    data_dict = {
        'sort': 'package_count',
        'all_fields': True
    }
    groups = _get_action('group_list', {}, data_dict)
    groups = [group for group in groups if group.get('package_count') > 0]

    return groups
