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

from xml.dom.minidom import getDOMImplementation
import csv
from io import BytesIO, StringIO
import json
import codecs
import re
from logging import getLogger

from rdflib.namespace import Namespace, RDF, XSD, SKOS, RDFS
from rdflib import Literal, URIRef, BNode, Graph
from ckanext.dcat.utils import resource_uri
from ckan.model.license import LicenseRegister
from ckanext.dcat.processors import RDFSerializer
from ckan.common import config
from ckan.lib.helpers import helper_functions
from ckan.lib import mailer as ckan_mailer
import requests

import smtplib
from socket import error as socket_error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from smtplib import SMTPRecipientsRefused
from ckan.plugins.toolkit import _


log = getLogger(__name__)


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


_DEFAULT_OSM_OVERPASS_URL = "https://lz4.overpass-api.de/api/interpreter"


def export_resource_to_rdf(resource_dict, dataset_dict, _format='xml'):
    """Export the resource in RDF format.

    Builds an RDF Graph containing only the selected resource and exports it to the
    selected format (default ``xml``).

    :param dict resource_dict: resource metadata.
    :param dict dataset_dict: dataset metadata.
    :param str _format: export format. Default is ``xml``.

    :returns: the serialized RDF graph of the resource.
    :rtype: 
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
    :rtype:
    """
    return export_dict_to_xml(resource_dict, 'resource')


def export_package_to_xml(package_dict):
    """Export package metadata to XML format.

    :param dict package_dict: the package metadata.

    :returns: XML representation of the package metadata.
    :rtype: string
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

    for prop, value in value_dict.items():
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
        for prop, val in value.items():
            _add_element(doc, dict_el, prop, val)
    else:
        _add_simple_element(doc, parent_el, element_name, value)


def _add_simple_element(doc, parent_el, element_name, value):
    el = doc.createElement(element_name)

    if not isinstance(value, str) and not isinstance(value, str):
        value = str(value)
    if not isinstance(value, str):
        value = str(value)
    txt = doc.createTextNode(value)
    el.appendChild(txt)
    parent_el.appendChild(el)


def to_utf8_str(value):
    """Convert the value to 'UTF-8' encoded string safely.

    :param value: the value to be converted to UTF-8 string.

    :returns: UTF-8 representation of the provided value.
    """
    if isinstance(value, str):
        return value
    else:
        return str(value)


class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
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

    fieldnames = [prop for prop,_ in value_dict.items()]

    writer = UnicodeWriter(stream)

    row = []
    for prop in fieldnames:
        val = value_dict[prop]
        if isinstance(val, list) or isinstance(val, dict):
            val = json.dumps(val, ensure_ascii=False)
        row.append(to_utf8_str(val))
    
    writer.writerow([to_utf8_str(f) for f in fieldnames])
    writer.writerow(row)

    return stream.getvalue()


def get_package_location_geojson(package_dict):
    """Retrieve spatial data in GeoJSON string for this package.

    The package is checked if it contains spatial_uri and if so, the
    GeoJSON spatial data is fetched for that spatial_uri.

    :param dict package_dict: the package data dict.

    :returns: ``str`` the GeoJSON data string.
    """

    location_uri = package_dict.get('spatial_uri')
    if not location_uri:
        return None
    location_uri = _code_to_spatial_uri(location_uri)
    resource_id = _extract_spatial_resource_id(location_uri)
    if not resource_id:
        return None

    geojson_value = _get_geojson(resource_id)
    return geojson_value


def populate_location_name_from_spatial_uri(package_dict):
    """Populates location name from spatial URI
    """
    if package_dict.get('spatial_uri'):
        try:
            name = _get_helper('mk_dcatap_spatial_name_from_code')(package_dict['spatial_uri'])
            if name:
                package_dict['extras_spatial_location_name'] = name
        except Exception as e:
            log.debug('Failed to set location name: %s', e)


def _extract_spatial_resource_id(location_uri):
    """Extracts the resource_id from the spatial URI.
    """
    match = re.search('/(?P<relation_id>\\d+)$', str(location_uri))
    if match:
        return match.group('relation_id')
    return None


def _fetch_osm_relation(relation_id):
    """Fetches the Openstreetmap data for the given relation. The important
    data fetched is the bounding box.

    Uses the OSM overpass API.
    """
    overpass_interpeter_url = config.get('ckanext.datagovmk.osm_overpass_url', _DEFAULT_OSM_OVERPASS_URL)
    overpass_query = "[out:json];(relation(id:{relation_id})[boundary=administrative];);out bb;".format(relation_id=relation_id)
    try:
        resp = requests.post(overpass_interpeter_url, data=overpass_query)
        if resp and resp.status_code == 200:
            return resp.json()
        log.warning('Unable to fetch geometry data from openstreetmap. Remote server responded with error: %d - %s', resp.status_code, resp.text)
        return None
    except Exception as e:
        log.warning(e)
        return None


def _fetch_geom(resource):
    """Fetches the bounding box from OSM and transforms it to a 5-point ``Polygon`` geometry 
    supported by CKAN.
    """
    data = _fetch_osm_relation(resource)
    if not data:
        return None
    
    if data.get('elements'):
        bounds = data['elements'][0].get('bounds')
        if bounds:
            minlat = bounds['minlat']
            maxlat = bounds['maxlat']
            minlon = bounds['minlon']
            maxlon = bounds['maxlon']

            geom = {
                'type': 'Polygon',
                'coordinates': [
                    [
                        [minlon, maxlat],
                        [minlon, minlat],
                        [maxlon, minlat],
                        [maxlon, maxlat],
                        [minlon, maxlat]  # just a copy of the first one, close the Polygon
                    ]
                ]
            }

            return geom
    return None

def _get_geojson(resource):
    """Retrieves the GeoJSON 5-point Polygon geom for the specified resource.
    """
    geojson_dict = _fetch_geom(resource)
    if geojson_dict:
        return json.dumps(geojson_dict)
    return None


def _get_helper(helper):
    return helper_functions.get(helper)


def _code_to_spatial_uri(code):
    code_to_uri = _get_helper('mk_dcatap_spatial_uri_from_code')
    if code_to_uri:
        uri = code_to_uri(code)
        return uri or code
    return code



def send_email(to_name, to_email, subject, content):
    """ This function sends e-mail
    """
    content = """\
        <html>
          <head></head>
          <body>
            """ + content + """
          </body>
        </html>
    """
    try:
        ckan_mailer.mail_recipient(to_name, to_email, subject, content, headers={
            'Content-Type': 'text/html; charset=utf-8'
        })
        return {
            'success': True,
            'message': _('Email message was successfully sent.')
        }
    except Exception as e:
        log.exception(e)
        return {
            'success': False,
            'message': _('An error occured while sending the email. Try again.')
        }