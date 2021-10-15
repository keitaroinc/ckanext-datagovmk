from ckanext.datastore.blueprint import datastore, PAGINATE_BY, DUMP_FORMATS, int_validator, boolean_validator



def dump(resource_id):
    try:
        offset = int_validator(request.GET.get('offset', 0), {})
    except toolkit.Invalid as e:
        toolkit.abort(400, u'offset: ' + e.error)
    try:
        limit = int_validator(request.GET.get('limit'), {})
    except toolkit.Invalid as e:
        toolkit.abort(400, u'limit: ' + e.error)
    bom = boolean_validator(request.GET.get('bom'), {})
    fmt = request.GET.get('format', 'csv')

    if fmt not in DUMP_FORMATS:
        toolkit.abort(400, _(
            u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

    try:
        dump_to(
            resource_id,
            response,
            fmt=fmt,
            offset=offset,
            limit=limit,
            options={u'bom': bom})
    except toolkit.ObjectNotFound:
        toolkit.abort(404, _('DataStore resource not found'))



datastore.add_url_rule('datastore/dump/<resource_id>', view_func=dump, methods=['GET'])