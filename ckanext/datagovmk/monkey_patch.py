"""
Copyright (c) 2018 Keitaro AB

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Affero General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Affero General Public License for more details.

You should have received a copy of the GNU Affero General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from ckan.lib import activity_streams as core_activity_streams
from ckan.logic import validators as core_validators
from ckan.plugins import toolkit


def activity_stream_string_updated_user_general_authority(context, activity):
    activity_data = activity.get('data')
    previous_authority_file = activity_data.get('previous_authority_file')
    current_authority_file = activity_data.get('current_authority_file')
    message = toolkit._(u'''
    replaced their <a href="{previous_authority_file}" target="_blank">old</a>
    general authority file with a <a href="{current_authority_file}"
    target="_blank">new</a> one''').format(
        previous_authority_file=previous_authority_file,
        current_authority_file=current_authority_file
    )
    return toolkit._('{actor} ' + message)


def activity_stream_string_dataset_agreement_general_authority(context, activity):
    activity_data = activity.get('data')
    current_authority_file = activity_data.get('current_authority_file')
    dataset_url = activity_data.get('dataset_url')
    dataset_name = activity_data.get('dataset_name')
    message = toolkit._(u'''agreed to create the dataset <a href="{dataset_url}">
    {dataset_name}</a> using general <a href="{current_authority_file}"
    target="_blank">authority file</a>''').format(
        current_authority_file=current_authority_file,
        dataset_url=dataset_url,
        dataset_name=dataset_name
    )
    return toolkit._('{actor} ' + message)


def activity_stream_string_dataset_agreement_additional_authority(context, activity):
    activity_data = activity.get('data')
    current_authority_file = activity_data.get('current_authority_file')
    dataset_url = activity_data.get('dataset_url')
    dataset_name = activity_data.get('dataset_name')
    message = toolkit._(u'''agreed to create the dataset <a href="{dataset_url}">
    {dataset_name}</a> using additional <a href="{current_authority_file}"
    target="_blank">authority file</a>''').format(
        current_authority_file=current_authority_file,
        dataset_url=dataset_url,
        dataset_name=dataset_name
    )
    return toolkit._('{actor} ' + message)


def activity_streams():
    _activity_stream_string_functions =\
        core_activity_streams.activity_stream_string_functions
    _activity_stream_string_functions['updated_user_general_authority'] =\
        activity_stream_string_updated_user_general_authority
    _activity_stream_string_functions['dataset_agreement_general_authority'] =\
        activity_stream_string_dataset_agreement_general_authority
    _activity_stream_string_functions['dataset_agreement_additional_authority'] =\
        activity_stream_string_dataset_agreement_additional_authority
    core_activity_streams.activity_stream_string_functions =\
        _activity_stream_string_functions


def validators():
    _object_id_validators = core_validators.object_id_validators
    _object_id_validators['updated_user_general_authority'] =\
        core_validators.user_id_or_name_exists
    _object_id_validators['dataset_agreement_general_authority'] =\
        core_validators.user_id_or_name_exists
    _object_id_validators['dataset_agreement_additional_authority'] =\
        core_validators.user_id_or_name_exists
    core_validators.object_id_validators = _object_id_validators
