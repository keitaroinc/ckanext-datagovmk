"""
Helpers and tools to check and use the stats tables from ckanext-googleanalytics.
"""

from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy.sql import select, text
from sqlalchemy import func

import ckan.model as model


TABLES = {}

_STATS_CHECKED = False




def _setup_stats_tables():
    if _STATS_CHECKED:
        return

    metadata = MetaData()

    package_stats = Table('package_stats', metadata,
                        Column('package_id', String(60),
                                primary_key=True),
                        Column('visits_recently', Integer),
                        Column('visits_ever', Integer))
    resource_stats = Table('resource_stats', metadata,
                        Column('resource_id', String(60),
                                primary_key=True),
                        Column('visits_recently', Integer),
                        Column('visits_ever', Integer))
    
    engine = model.meta.engine


    if engine.dialect.has_table(engine, 'package_stats'):
        TABLES['package_stats'] = package_stats
    
    if engine.dialect.has_table(engine, 'resource_stats'):
        TABLES['resource_stats'] = resource_stats
    
    global _STATS_CHECKED
    _STATS_CHECKED = True


def is_stats_available():
    _setup_stats_tables()
    return 'package_stats' in TABLES and 'resource_stats' in TABLES


def get_stats_for_package(package_id):
    if not is_stats_available():
        return {}
    package_stats = TABLES['package_stats']
    results = model.Session.execute(select([package_stats.c.package_id,
                                            package_stats.c.visits_recently,
                                            package_stats.c.visits_ever]).\
                                    where(package_stats.c.package_id == package_id)).\
                                    fetchmany(1)
    if results:
        stats_tuple = results[0]
        return {'id': stats_tuple[0], 'visits_recently': stats_tuple[1], 'visits_ever': stats_tuple[2]}
    return {}

def get_stats_for_resource(resource_id):
    if not is_stats_available():
        return {}
    resource_stats = TABLES['resource_stats']
    results = model.Session.execute(select([resource_stats.c.resource_id,
                                            resource_stats.c.visits_recently,
                                            resource_stats.c.visits_ever]).\
                                    where(resource_stats.c.resource_id == resource_id)).\
                                    fetchmany(1)
    if results:
        stats_tuple = results[0]
        return {'id': stats_tuple[0], 'visits_recently': stats_tuple[1], 'visits_ever': stats_tuple[2]}
    return {}