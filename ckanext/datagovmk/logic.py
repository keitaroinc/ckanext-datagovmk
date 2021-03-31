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

import ckanext.datagovmk.utils as utils


def import_spatial_data(package_dict):
    """Import spatial data for a given package.

    The spatial geometry, if available, is saved in the package extras
    under key ``spatial``. This is compatible with ckanext-spatial and
    the package will be indexed and available for geo-spatial search.

    :param dict package_dict: the package data dict.

    """
    geojson_data = utils.get_package_location_geojson(package_dict)
    if geojson_data:
        spatial_extra = {'key': 'spatial', 'value': geojson_data}
        i = 0
        has_spatial = False
        for extra in package_dict.get('extras', []):
            if extra['key'] == 'spatial':
                package_dict['extras'][i] = spatial_extra
                has_spatial = True
                break
            i += 1
        if not has_spatial:
            if not package_dict.get('extras'):
                package_dict['extras'] = []
            package_dict['extras'].append(spatial_extra)