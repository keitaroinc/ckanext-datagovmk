from xml.dom.minidom import getDOMImplementation
import csv
from io import BytesIO
import cStringIO
import json
import codecs

from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from rdflib import Literal, URIRef, BNode, Graph
from ckanext.dcat.utils import resource_uri
from ckan.model.license import LicenseRegister
from ckanext.dcat.processors import RDFSerializer



DCT = Namespace("http://purl.org/dc/terms/")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
ADMS = Namespace("http://www.w3.org/ns/adms#")
VCARD = Namespace("http://www.w3.org/2006/vcard/ns#")
FOAF = Namespace("http://xmlns.com/foaf/0.1/")
SCHEMA = Namespace('http://schema.org/')
TIME = Namespace('http://www.w3.org/2006/time')
LOCN = Namespace('http://www.w3.org/ns/locn#')
GSP = Namespace('http://www.opengis.net/ont/geosparql#')
OWL = Namespace('http://www.w3.org/2002/07/owl#')
SPDX = Namespace('http://spdx.org/rdf/terms#')


def export_resource_to_rdf(resource_dict, dataset_dict, _format='xml'):
    """Export the resource in RDF format.

    Builds an RDF Graph containing only the selected resource and exports it to the
    selected format (default ``xml``).

    :param dict resource_dict: resource metadata.
    :param dict dataset_dict: dataset metadata.
    :param str _format: export format. Default is ``xml``.

    :returns: the serialized RDF graph of the resource.
    """
    g = Graph()

    distribution = URIRef(resource_uri(resource_dict))

    g.add((distribution, RDF.type, DCAT.Distribution))

    if 'license' not in resource_dict and 'license_id' in dataset_dict:
        lr = LicenseRegister()
        _license = lr.get(dataset_dict['license_id'])
        resource_dict['license'] = _license.url

    #  Simple values
    items = [
        ('name', DCT.title, None, Literal),
        ('description', DCT.description, None, Literal),
        ('status', ADMS.status, None, Literal),
        ('rights', DCT.rights, None, Literal),
        ('license', DCT.license, None, URIRef),
    ]

    for itm in items:
        key, rdf_prop, def_value, rdf_type = itm
        value = resource_dict.get(key, def_value)
        if value:
            g.add((distribution, rdf_prop, rdf_type(value)))

    #  Lists
    items = [
        ('documentation', FOAF.page, None, URIRef),
        ('language', DCT.language, None, URIRef),
        ('conforms_to', DCT.conformsTo, None, URIRef),
    ]
    # self._add_list_triples_from_dict(resource_dict, distribution, items)
    for itm in items:
        key, rdf_prop, def_value, rdf_type = itm
        value = resource_dict.get(key, def_value)
        if value:
            if isinstance(value, list):
                for val in value:
                    g.add((distribution, rdf_prop, rdf_type(val)))
            else:
                g.add((distribution, rdf_prop, rdf_type(value)))


    # Format
    if '/' in resource_dict.get('format', ''):
        g.add((distribution, DCAT.mediaType,
                Literal(resource_dict['format'])))
    else:
        if resource_dict.get('format'):
            g.add((distribution, DCT['format'],
                    Literal(resource_dict['format'])))

        if resource_dict.get('mimetype'):
            g.add((distribution, DCAT.mediaType,
                    Literal(resource_dict['mimetype'])))

    # URL
    url = resource_dict.get('url')
    download_url = resource_dict.get('download_url')
    if download_url:
        g.add((distribution, DCAT.downloadURL, URIRef(download_url)))
    if (url and not download_url) or (url and url != download_url):
        g.add((distribution, DCAT.accessURL, URIRef(url)))

    # Dates
    items = [
        ('issued', DCT.issued, None, Literal),
        ('modified', DCT.modified, None, Literal),
    ]

    #self._add_date_triples_from_dict(resource_dict, distribution, items)
    for itm in items:
        key, rdf_prop, def_value, rdf_type = itm
        value = resource_dict.get(key, def_value)
        if value:
            g.add((distribution, rdf_prop, rdf_type(value)))

    # Numbers
    if resource_dict.get('size'):
        try:
            g.add((distribution, DCAT.byteSize,
                    Literal(float(resource_dict['size']),
                            datatype=XSD.decimal)))
        except (ValueError, TypeError):
            g.add((distribution, DCAT.byteSize,
                    Literal(resource_dict['size'])))
    # Checksum
    if resource_dict.get('hash'):
        checksum = BNode()
        g.add((checksum, SPDX.checksumValue,
                Literal(resource_dict['hash'],
                        datatype=XSD.hexBinary)))

        if resource_dict.get('hash_algorithm'):
            if resource_dict['hash_algorithm'].startswith('http'):
                g.add((checksum, SPDX.algorithm,
                        URIRef(resource_dict['hash_algorithm'])))
            else:
                g.add((checksum, SPDX.algorithm,
                        Literal(resource_dict['hash_algorithm'])))
        g.add((distribution, SPDX.checksum, checksum))
    
    return g.serialize(format=_format)


def export_resource_to_xml(resource_dict):
    """Exports the selected resource metadata as XML.

    :param dict resource_dict: resource metadata.

    :returns: serialized data as XML string.
    """
    return export_dict_to_xml(resource_dict, 'resource')


def export_package_to_xml(package_dict):
    """Export package metadata to XML format.

    :param dict package_dict: the package metadata.

    :returns: XML representation (as string) of the package metadata.
    """
    return export_dict_to_xml(package_dict, 'package')


def export_dict_to_xml(value_dict, root_name):
    """Export a dictionary data as XML string.

    :param dict value_dict: the dictionary holding the data to be exported.
    :param str root_name: the name of the root element in the XML DOM.

    :returns: XML representation (without namespaces) of the provided dictionary.
    """
    impl = getDOMImplementation()

    doc = impl.createDocument(None, root_name, None)

    root = doc.documentElement

    for prop, value in value_dict.iteritems():
        _add_element(doc, root, prop, value)

    xml = doc.toprettyxml()
    return xml


def export_package_to_rdf(package_dict, _format='xml'):
    """Exports a package metadata in RDF in the specified format.

    :param dict package_dict: the package metadata.
    :param str _format: the desired format to export to. Default is ``xml``.
    """
    serializer = RDFSerializer()
    return serializer.serialize_dataset(package_dict, _format=_format)


def _add_element(doc, parent_el, element_name, value):
    if isinstance(value, list):
        for val in value:
            _add_element(doc, parent_el, element_name, val)
    elif isinstance(value, dict):
        dict_el = doc.createElement(element_name)
        parent_el.appendChild(dict_el)
        for prop, val in value.iteritems():
            _add_element(doc, dict_el, prop, val)
    else:
        _add_simple_element(doc, parent_el, element_name, value)


def _add_simple_element(doc, parent_el, element_name, value):
    el = doc.createElement(element_name)

    if not isinstance(value, str) and not isinstance(value, unicode):
        value = str(value)
    if not isinstance(value, unicode):
        value = unicode(value, 'utf-8')
    txt = doc.createTextNode(value)
    el.appendChild(txt)
    parent_el.appendChild(el)


def to_utf8_str(value):
    """Convert the value to 'UTF-8' encoded string safely.

    :param value: the value to be converted to UTF-8 string.

    :returns: UTF-8 representation of the provided value.
    """
    if isinstance(value, str):
        return unicode(value, 'utf-8')
    elif isinstance(value, unicode):
        return value
    else:
        return unicode(str(value), 'utf-8')


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = cStringIO.StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)


def export_dict_to_csv(value_dict):
    """Exports the provided dictionary as CSV file.

    :param dict value_dict: dictionary to be serialized.

    :returns: serialized CSV representation of the dict data.
    """
    stream = BytesIO()

    fieldnames = [prop for prop,_ in value_dict.iteritems()]

    writer = UnicodeWriter(stream)

    row = []
    for prop in fieldnames:
        val = value_dict[prop]
        if isinstance(val, list) or isinstance(val, dict):
            val = json.dumps(val)
        row.append(to_utf8_str(val))
    
    writer.writerow([to_utf8_str(f) for f in fieldnames])
    writer.writerow(row)

    return stream.getvalue()