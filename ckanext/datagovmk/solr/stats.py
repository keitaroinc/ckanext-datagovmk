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


import logging
import socket

import pysolr
from ckan.lib.search.common import make_connection

log = logging.getLogger(__name__)


def update_package_stats(package_id, stats):
    try:
        conn = make_connection()
        query = "id:%s" % package_id
        res = conn.search(q=query)
        if res and res.docs:
            pkg_dict = res.docs[0]
            for key, value in stats.items():
                pkg_dict["extras_%s" % key] = str(value or '0').rjust(24, '0')

            if '_version_' in pkg_dict:
                del pkg_dict['_version_']
            conn.add(docs=[pkg_dict], commit=True)
    except pysolr.SolrError, e:
        log.error("Solr returned error: %s", e)
        log.exception(e)
        return
    except socket.error, e:
        log.error("Failed to connect to Solr server: %s", e)
        log.exception(e)
        return

def increment_total_downloads(package_id):
    try:
        conn = make_connection()
        query = "id:%s" % package_id
        res = conn.search(q=query)
        if res and res.docs:
            pkg_dict = res.docs[0]
            total_downloads = int(pkg_dict.get('extras_total_downloads', 0))
            total_downloads += 1
            pkg_dict["extras_total_downloads"] = str(total_downloads).rjust(24, '0')

            if '_version_' in pkg_dict:
                del pkg_dict['_version_']
            conn.add(docs=[pkg_dict], commit=True)
    except pysolr.SolrError, e:
        log.error("Solr returned error: %s", e)
        log.exception(e)
        return
    except socket.error, e:
        log.error("Failed to connect to Solr server: %s", e)
        log.exception(e)
        return