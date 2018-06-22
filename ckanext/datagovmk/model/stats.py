"""
Helpers and tools to check and use the stats tables from ckanext-googleanalytics.
"""

from sqlalchemy import Table, Column, Integer, String, MetaData
from sqlalchemy.sql import select, text, exists, update, insert
from sqlalchemy import func
from sqlalchemy.engine import reflection

import ckan.model as model


TABLES = {}

global _STATS_CHECKED
_STATS_CHECKED = False


def ensure_column(table_name, column_name, column_type, engine):
    """Ensure that the column exists in the table. If not, add it.

    :param str table_name: the table to check.
    :param str column_name: the name of the column to check for.
    :param str colmn_type: column type definition.
    :param sqlachemy.engine.Engine engine: configured SQLAlchemy engine.
    """
    insp = reflection.Inspector.from_engine(engine)
    has_column = False
    for col in insp.get_columns(table_name):
        if column_name == col['name']:
            has_column = True
            break
    
    if not has_column:
        engine.execute('ALTER TABLE %(table_name)s ADD COLUMN %(column_name)s %(column_type)s' % {
            "table_name": table_name,
            "column_name": column_name,
            "column_type": column_type
        })


def _setup_stats_tables():
    """Setup the tables for stats. This depends on ckanext-googleanalytics to create the tables in CKAN.
    """
    global _STATS_CHECKED
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
                        Column('visits_ever', Integer),
                        Column('downloads', Integer))
    
    engine = model.meta.engine


    if engine.dialect.has_table(engine, 'package_stats'):
        TABLES['package_stats'] = package_stats
    
    if engine.dialect.has_table(engine, 'resource_stats'):
        TABLES['resource_stats'] = resource_stats
        ensure_column('resource_stats', 'downloads', 'INTEGER', engine)
    
    _STATS_CHECKED = True


def is_stats_available():
    """Check if stats tables have been set up.

    :returns: ``bool`` True if the tables have been set up and we can use stats.
    """
    _setup_stats_tables()
    return 'package_stats' in TABLES and 'resource_stats' in TABLES


def get_stats_for_package(package_id):
    """Retrieve stats for the package.

    :param str package_id: the id of the package to retrieve stats for.

    :returns: ``dict``, the package stats. If no stats available, returns an empty dict.
      Available dict values are:
      * ``id`` - the package id
      * ``visits_recently`` - number of recent visits.
      * ``visits_ever`` - total number of visits to this package.

    """
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
    """Retrieve stats for the package.

    :param str resource_id: the id of the resource to retrieve stats for.

    :returns: ``dict``, the resource stats. If no stats available, returns an empty dict.
      Available dict values are:
      * ``id`` - the package id
      * ``visits_recently`` - number of recent visits.
      * ``visits_ever`` - total number of visits to this package.
      * ``downloads`` - total number of downloads of this resource.

    """
    if not is_stats_available():
        return {}
    resource_stats = TABLES['resource_stats']
    results = model.Session.execute(select([resource_stats.c.resource_id,
                                            resource_stats.c.visits_recently,
                                            resource_stats.c.visits_ever,
                                            resource_stats.c.downloads]).\
                                    where(resource_stats.c.resource_id == resource_id)).\
                                    fetchmany(1)
    if results:
        stats_tuple = results[0]
        return {'id': stats_tuple[0], 'visits_recently': stats_tuple[1], 'visits_ever': stats_tuple[2], 'downloads': stats_tuple[3]}
    return {}


def increment_downloads(resource_id):
    """Increments the number of downloads for the resource with ``resource_id``.

    :param str resource_id: the id of the resource which downloads count should be incremented.

    """
    if not is_stats_available():
        return
    resource_stats = TABLES['resource_stats']
    ret = model.Session.query(exists().where(resource_stats.c.resource_id == resource_id)).scalar()
    if not ret:
        model.Session.add(resource_stats(resource_id=resource_id, visits_recently=0, visits_ever=0, downloads=1))
    else:
        result = model.Session.query(resource_stats).filter_by(resource_id=resource_id).first()
        if result[3] is None:
            model.Session.execute(resource_stats.update(resource_stats.c.resource_id==resource_id).values(downloads=1))
        else:
            model.Session.execute(resource_stats.update(resource_stats.c.resource_id==resource_id).values(downloads=resource_stats.c.downloads+1))
    model.Session.commit()


def get_total_package_downloads(package_id):
    """Retrieve the total number of dowloads for all resources that belong to this package.

    :param str package_id: the package id.

    :returns: ``int``, the total number of downloads for all resources for this package id. This is the
        sum of the downloads count for all resurces that belong to this package.
    """
    if not is_stats_available():
        return
    resource_stats = TABLES['resource_stats']

    subq = model.Session.query(model.Resource.id).filter(model.Resource.package_id == package_id)

    result = model.Session.query(func.sum(resource_stats.c.downloads)).filter(resource_stats.c.resource_id.in_(subq)).scalar()
    return result or 0