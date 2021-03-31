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

def get_related_datasets(context, data_dict):

    '''This is an authentication function which allows only
    registered users to access the action

    :py:func:`~ckanext.datagovmk.actions.get_related_datasets`

    '''

    return {'success': True}


def start_script(context, data_dict):
    """ This is a sensitive action, so only sysadmins are allowed to execute
    it """
    return {'success': False}
