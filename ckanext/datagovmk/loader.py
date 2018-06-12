"""
Load either yaml or json, based on the name of the resource
"""

import json
from paste.reloader import watch_file

import os
import inspect


def load(f):
    if is_yaml(f.name):
        import yaml
        return yaml.load(f)
    return json.load(f)

def loads(s, url):
    if is_yaml(url):
        import yaml
        return yaml.load(s)
    return json.loads(s)

def is_yaml(n):
    return n.lower().endswith(('.yaml', '.yml'))

def load_schema_module_path(url):
    """
    Given a path like "ckanext.spatialx:spatialx_schema.json"
    find the second part relative to the import path of the first
    """

    module, file_name = url.split(':', 1)
    try:
        # __import__ has an odd signature
        m = __import__(module, fromlist=[''])
    except ImportError:
        return
    p = os.path.join(os.path.dirname(inspect.getfile(m)), file_name)
    if os.path.exists(p):
        watch_file(p)
        return load(open(p))