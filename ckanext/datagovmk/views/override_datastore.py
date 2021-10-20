from flask import Flask, Blueprint, make_response
from logging import getLogger
from contextlib import contextmanager
from six import text_type
from xml.etree.cElementTree import Element, SubElement, ElementTree
from codecs import BOM_UTF8

from ckan.plugins import toolkit
from ckan.plugins.toolkit import _, request
from ckanext.datastore.blueprint import (PAGINATE_BY,
                                         DUMP_FORMATS,
                                         int_validator,
                                         boolean_validator,
                                         dump)
from ckanext.datastore.writer import (
    csv_writer,
    tsv_writer,
    json_writer,
)

log = getLogger(__name__)

override_datastore = Blueprint('override_datastore', __name__)

SPECIAL_CHARS = u'#$%&!?@}{[]'


def dump_override(resource_id):
    try:
        offset = int_validator(request.args.get('offset', 0), {})
    except toolkit.Invalid as e:
        toolkit.abort(400, u'offset: ' + e.error)
    try:
        limit = int_validator(request.args.get('limit'), {})
    except toolkit.Invalid as e:
        toolkit.abort(400, u'limit: ' + e.error)
    bom = boolean_validator(request.args.get('bom'), {})
    fmt = request.args.get('format', 'csv')

    if fmt not in DUMP_FORMATS:
        toolkit.abort(400, _(
            u'format: must be one of %s') % u', '.join(DUMP_FORMATS))

    response = make_response()
    response.headers[u'content-type'] = u'application/octet-stream'

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

    return response


def get_xml_element(element_name):
    '''Return element name according XML naming standards
    Capitalize every word and remove special characters
    :param element_name: xml element
    :type element_name: str
    :returns: Element name according XML standards
    :rtype: str
    '''
    clean_word = u''.join(c.strip(SPECIAL_CHARS) for c in element_name)
    if str(clean_word).isnumeric():
        return u'_' + str(element_name)
    first, rest = clean_word.split(u' ')[0], clean_word.split(u' ')[1:]
    return first + u''.join(w.capitalize()for w in rest)


def dump_to(resource_id, output, fmt, offset, limit, options):
    """ Overriden method """
    if fmt == 'csv':
        writer_factory = csv_writer
        records_format = 'csv'
    elif fmt == 'tsv':
        writer_factory = tsv_writer
        records_format = 'tsv'
    elif fmt == 'json':
        writer_factory = json_writer
        records_format = 'lists'
    elif fmt == 'xml':
        writer_factory = xml_writer
        records_format = 'objects'

    def start_writer(fields):
        bom = options.get(u'bom', False)
        return writer_factory(output, fields, resource_id, bom)

    def result_page(offs, lim):
        return toolkit.get_action('datastore_search')(None, {
            'resource_id': resource_id,
            'limit': PAGINATE_BY
            if limit is None else min(PAGINATE_BY, lim),
            'offset': offs,
            'sort': '_id',
            'records_format': records_format,
            'include_total': 'false',  # XXX: default() is broken
        })

    result = result_page(offset, limit)

    with start_writer(result['fields']) as wr:
        while True:
            if limit is not None and limit <= 0:
                break

            records = result['records']

            wr.write_records(records)

            if records_format == 'objects' or records_format == 'lists':
                if len(records) < PAGINATE_BY:
                    break
            elif not records:
                break

            offset += PAGINATE_BY
            if limit is not None:
                limit -= PAGINATE_BY
                if limit <= 0:
                    break

            result = result_page(offset, limit)


class XMLWriter(object):
    """ Overriden class """
    _key_attr = u'key'
    _value_tag = u'value'

    def __init__(self, response, columns):
        self.response = response
        self.id_col = columns[0] == u'_id'
        if self.id_col:
            columns = columns[1:]
        self.columns = columns

    def _insert_node(self, root, k, v, key_attr=None):
        element = SubElement(root, k)
        if v is None:
            element.attrib[u'xsi:nil'] = u'true'
        elif not isinstance(v, (list, dict)):
            element.text = text_type(v)
        else:
            if isinstance(v, list):
                it = enumerate(v)
            else:
                it = v.items()
            for key, value in it:
                self._insert_node(element, self._value_tag, value, key)

        if key_attr is not None:
            element.attrib[self._key_attr] = text_type(key_attr)

    def write_records(self, records):
        """ Overriden """
        for r in records:
            root = Element(u'row')
            if self.id_col:
                root.attrib[u'_id'] = text_type(r[u'_id'])
            for c in self.columns:
                node_name = get_xml_element(c)
                self._insert_node(root, node_name, r[c])
            ElementTree(root).write(self.response, encoding=u'utf-8')
            self.response.write(b'\n')


@contextmanager
def xml_writer(response, fields, name=None, bom=False):
    u'''Context manager for writing UTF-8 XML data to response

    :param response: file-like or response-like object for writing
        data and headers (response-like objects only)
    :param fields: list of datastore fields
    :param name: file name (for headers, response-like objects only)
    :param bom: True to include a UTF-8 BOM at the start of the file
    '''

    if hasattr(response, u'headers'):
        response.headers['Content-Type'] = (b'text/xml; charset=utf-8')
        if name:
            response.headers['Content-disposition'] = bytes(
                u'attachment; filename="{name}.xml"'.format(
                    name=name), encoding='utf8')
    if bom:
        response.stream.write(BOM_UTF8)
    response.stream.write(b'<data>\n')
    yield XMLWriter(response.stream, [f['id'] for f in fields])
    response.stream.write(b'</data>\n')


# For OVERRIDING the Ckan datastore blueprint
# # map of views which we won't register in Flask app
# # you can store this somewhere in settings
SKIP_VIEWS = (
    # route, view function
    ('/datastore/dump/<resource_id>', dump, ),
)


class CustomFlask(Flask):

    def add_url_rule(self, rule, endpoint=None, view_func=None, **options):
        # Flask registers views when an application starts
        # do not add view from SKIP_VIEWS
        for rule_, view_func_ in SKIP_VIEWS:  # type: str, func
            if rule_ == rule and view_func == view_func_:
                return
        return super(CustomFlask, self).\
            add_url_rule(rule, endpoint, view_func, **options)


app = CustomFlask(__name__)
app.register_blueprint(override_datastore)

override_datastore.add_url_rule("/datastore/dump/<resource_id>",
                                view_func=dump_override)
