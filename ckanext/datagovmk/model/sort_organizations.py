import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc

__all__ = [
    'SortOrganizations',
    'sort_organizations_table',
    'setup'
]

sort_organizations_table = Table(
    'sort_organizations',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('org_id', types.UnicodeText, ForeignKey('group.id', ondelete='CASCADE')),
    Column('title_mk', types.UnicodeText),
    Column('title_en', types.UnicodeText),
    Column('title_sq', types.UnicodeText)

)

class SortOrganizations(DomainObject):

    @classmethod
    def get_all(cls, limit=5):
        obj = Session.query(cls).autoflush(False)
        return obj.limit(limit).all()



mapper(
    SortOrganizations,
    sort_organizations_table
)


def setup():
    metadata.create_all(model.meta.engine)
