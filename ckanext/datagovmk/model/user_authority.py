import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table, desc

__all__ = ['UserAuthority', 'user_authority_table', 'setup']

user_authority_table = None

class UserAuthority(DomainObject):

    @classmethod
    def get(cls, **kwargs):
        obj = Session.query(cls).autoflush(False)
        obj = obj.filter_by(**kwargs).first()

        if obj:
            return obj
        else:
            return None

    @classmethod
    def get_last_authority_for_user(cls, authority_type, user_id):
        obj = Session.query(cls).autoflush(False)
        obj = obj.filter_by(user_id=user_id, authority_type=authority_type)
        obj = obj.order_by(desc('created')).first()

        if obj:
            return obj
        else:
            return None

    @classmethod
    def delete(cls, user_id, key):
        keywords = {'user_id':user_id, 'key':key}
        obj = Session.query(cls).filter_by(**keywords).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound


user_authority_table = Table(
    'user_authority',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('user_id', types.UnicodeText),
    Column('authority_file', types.UnicodeText),
    Column('authority_type', types.UnicodeText),
    Column('created', types.DateTime, default=datetime.datetime.now),
)

mapper(
    UserAuthority,
    user_authority_table,
)

def setup():
    metadata.create_all(model.meta.engine)
