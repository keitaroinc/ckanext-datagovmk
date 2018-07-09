import ckanext.datagovmk.utils as utils


def import_spatial_data(package_dict):
    import json
    print json.dumps(package_dict)
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