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