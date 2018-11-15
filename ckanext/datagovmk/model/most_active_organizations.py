import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc

__all__ = [
    'MostActiveOrganizations',
    'most_active_organizations_table',
    'setup'
]

most_active_organizations_table = None


class MostActiveOrganizations(DomainObject):

    @classmethod
    def get_all(cls, limit=5):
        obj = Session.query(cls).autoflush(False)
        return obj.limit(limit).all()

most_active_organizations_table = Table(
    'most_active_organizations',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('org_id', types.UnicodeText),
    Column('org_name', types.UnicodeText),
    Column('org_display_name', types.UnicodeText),
)

mapper(
    MostActiveOrganizations,
    most_active_organizations_table,
)


def setup():
    metadata.create_all(model.meta.engine)
