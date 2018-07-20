from ckan.lib import activity_streams as core_activity_streams
from ckan.logic import validators as core_validators
from ckan.plugins import toolkit


def activity_stream_string_updated_user_general_authority(context, activity):
    activity_data = activity.get('data')
    previous_authority_file = activity_data.get('previous_authority_file')
    current_authority_file = activity_data.get('current_authority_file')
    message = '''
    replaced their <a href="{previous_authority_file}" target="_blank">old</a>
    general authority file with a <a href="{current_authority_file}"
    target="_blank">new</a> one'''.format(
        previous_authority_file=previous_authority_file,
        current_authority_file=current_authority_file
    )
    return toolkit._('{actor} ' + message)


def activity_streams():
    _activity_stream_string_functions =\
        core_activity_streams.activity_stream_string_functions
    _activity_stream_string_functions['updated_user_general_authority'] =\
        activity_stream_string_updated_user_general_authority
    core_activity_streams.activity_stream_string_functions =\
        _activity_stream_string_functions


def validators():
    _object_id_validators = core_validators.object_id_validators
    _object_id_validators['updated_user_general_authority'] =\
        core_validators.user_id_or_name_exists
    core_validators.object_id_validators = _object_id_validators
