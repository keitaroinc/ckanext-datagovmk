import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table

user_authority_table = None


def setup():
    if user_authority_table is None:
        define_user_authority_table()

        if not user_authority_table.exists() and model.user_table.exists():
            user_authority_table.create()


class UserAuthority(DomainObject):

    @classmethod
    def get(cls, user_id, key, default=None):
        keywords = {'user_id':user_id, 'key':key}

        obj = Session.query(cls).autoflush(False)
        obj = obj.filter_by(**keywords).first()

        if obj:
            return obj
        else:
            return default

    @classmethod
    def delete(cls, user_id, key):
        keywords = {'user_id':user_id, 'key':key}
        obj = Session.query(cls).filter_by(**keywords).first()
        if obj:
            Session.delete(obj)
            Session.commit()
        else:
            raise logic.NotFound


def define_user_authority_table():
    global user_authority_table
    user_authority_table = Table(
        'user_authority',
        metadata,
        Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
        Column('user_id', types.UnicodeText, ForeignKey('user.id')),
        Column('authority_file', types.UnicodeText),
        Column('authority_type', types.UnicodeText),
        Column('dataset_id', types.UnicodeText),
        Column('created', types.DateTime, default=datetime.datetime.now),
    )

    mapper(
        UserAuthority,
        user_authority_table,
    )
