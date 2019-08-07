import datetime

import ckan.logic as logic
import ckan.lib.helpers as h

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
    def get(cls, id=None, **kwargs):
        q = kwargs.get('q')
        limit = kwargs.get('limit')
        offset = kwargs.get('offset')
        order_by = kwargs.get('order_by')
        current_lang = h.lang()

        kwargs.pop('q', None)
        kwargs.pop('limit', None)
        kwargs.pop('offset', None)
        kwargs.pop('order_by', None)

        query = Session.query(cls).autoflush(False)
        query = query.filter_by(**kwargs)

        if id:
            query = query.filter(
                or_(cls.id == id, cls.id == id)
            )

        if q:
            if current_lang == 'mk':
                query = query.filter(
                    or_(cls.title_mk.contains(q), cls.title_mk.ilike(r"%{}%".format(q)))
                )
            elif current_lang == 'en':
                query = query.filter(
                    or_(cls.title_en.contains(q), cls.title_en.ilike(r"%{}%".format(q)))
                )
            else:
                query = query.filter(
                    or_(cls.title_sq.contains(q), cls.title_sq.ilike(r"%{}%".format(q)))
                )

        if order_by:
            query = query.order_by(order_by)

        if limit:
            query = query.limit(limit)

        if offset:
            query = query.offset(offset)

        return query

    @classmethod
    def update(cls, filter, data):
        obj = Session.query(cls).filter_by(**filter)
        obj.update(data)
        Session.commit()

        return obj.first()
        
    @classmethod
    def delete(cls, filter):
        obj = Session.query(cls).filter_by(**filter).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound


mapper(
    SortOrganizations,
    sort_organizations_table
)


def setup():
    metadata.create_all(model.meta.engine)
