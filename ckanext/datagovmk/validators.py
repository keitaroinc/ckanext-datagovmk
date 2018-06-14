from ckantoolkit import get_validator, UnknownValidator, missing, Invalid, _, get_converter
import ckanext.datagovmk.helpers as helpers
import datetime
import json


OneOf = get_validator('OneOf')
ignore_missing = get_validator('ignore_missing')
not_empty = get_validator('not_empty')

convert_to_extras = get_converter('convert_to_extras')
convert_from_extras = get_converter('convert_from_extras')


def schema_validator(fn):
    """
    Decorate a validator that needs to have the scheming fields
    passed with this function. When generating navl validator lists
    the function decorated will be called passing the field
    and complete schema to produce the actual validator for each field.
    """
    fn.is_a_schema_validator = True
    return fn


@schema_validator
def datagovmk_multiple_choice(field, schema):
    """
    Accept zero or more values from a list of choices and convert
    to a json list for storage:

    1. a list of strings, eg.:

       ["choice-a", "choice-b"]

    2. a single string for single item selection in form submissions:

       "choice-a"
    """
    static_choice_values = None
    if 'choices' in field:
        static_choice_order = [c['value'] for c in field['choices']]
        static_choice_values = set(static_choice_order)

    def validator(key, data, errors, context):
        # if there was an error before calling our validator
        # don't bother with our validation
        if errors[key]:
            return

        value = data[key]
        if value is not missing:
            if isinstance(value, basestring):
                value = [value]
            elif not isinstance(value, list):
                errors[key].append(_('expecting list of strings'))
                return
        else:
            value = []

        choice_values = static_choice_values
        if not choice_values:
            choice_order = [c['value'] for c in helpers.datagovmk_field_choices(field)]
            choice_values = set(choice_order)

        selected = set()
        for element in value:
            if element in choice_values:
                selected.add(element)
                continue
            errors[key].append(_('unexpected choice "%s"') % element)

        if not errors[key]:
            data[key] = json.dumps([v for v in
                (static_choice_order if static_choice_values else choice_order)
                if v in selected])

            if field.get('required') and not selected:
                errors[key].append(_('Select at least one'))

    return validator


@schema_validator
def datagovmk_multiple_choice_output(value):
    """
    return stored json as a proper list
    """
    if isinstance(value, list):
        return value
    try:
        return json.loads(value)
    except ValueError:
        return [value]


@schema_validator
def datagovmk_required(field, schema):
    """
    not_empty if field['required'] else ignore_missing
    """
    if field.get('required'):
        return not_empty
    return ignore_missing


@schema_validator
def datagovmk_choices(field, schema):
    """
    Require that one of the field choices values is passed.
    """
    if 'choices' in field:
        return OneOf([c['value'] for c in field['choices']])

    def validator(value):
        if value is missing or not value:
            return value
        choices = helpers.datagovmk_field_choices(field)
        for c in choices:
            if value == c['value']:
                return value
        raise Invalid(_('unexpected choice "%s"') % value)

    return validator


def validators_from_string(s, field, schema):
    """
    convert a schema validators string to a list of validators

    e.g. "if_empty_same_as(name) unicode" becomes:
    [if_empty_same_as("name"), unicode]
    """
    out = []
    parts = s.split()
    for p in parts:
        if '(' in p and p[-1] == ')':
            name, args = p.split('(', 1)
            args = args[:-1].split(',')  # trim trailing ')', break up
            v = get_validator_or_converter(name)(*args)
        else:
            v = get_validator_or_converter(p)
        if getattr(v, 'is_a_schema_validator', False):
            v = v(field, schema)
        out.append(v)
    return out


def get_validator_or_converter(name):
    """
    Get a validator or converter by name
    """
    if name == 'unicode':
        return unicode
    try:
        v = get_validator(name)
        return v
    except UnknownValidator:
        pass
    raise Exception('validator/converter not found: %r' % name)


def convert_to_json_if_date(date, context):
    if isinstance(date, datetime.datetime):
        return date.date().isoformat()
    elif isinstance(date, datetime.date):
        return date.isoformat()
    else:
        return date

def convert_to_json_if_datetime(date, context):
    if isinstance(date, datetime.datetime):
        return date.isoformat()

    return date


def create_schema(default_schema, schema_fields, presets, action="create"):
    merged_schema = {}
    merged_schema.update(default_schema)

    for field in schema_fields:
        field_validators = field.get("validators")
        if field_validators is None:
            if field.get("preset"):
                field_validators = presets.get(field['preset'],{}).get('validators')
        if field_validators is not None:
            field_validators = validators_from_string(field_validators, field, merged_schema)
        else:
            field_validators = []

        if action != 'show': # create/update
            if helpers.get_form_field_required(field):
                field_validators += [not_empty, unicode]
            else:
                field_validators += [ignore_missing, unicode]
            
            if field['field_name'] not in default_schema:
                field_validators += [convert_to_extras]
        else: # show - output validators
            if field['field_name'] not in default_schema:
                field_validators += [convert_from_extras, ignore_missing]
            else:
                field_validators += [ignore_missing]

        merged_schema[field['field_name']] = field_validators
        

    return merged_schema