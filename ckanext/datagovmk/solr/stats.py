
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