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

import datetime

import ckan.logic as logic
from ckan import model
from ckan.model.meta import metadata, mapper, Session
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

from sqlalchemy import types, ForeignKey, Column, Table


class UserAuthorityDataset(DomainObject):

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


user_authority_dataset_table = Table(
    'user_authority_dataset',
    metadata,
    Column('id', types.UnicodeText, primary_key=True, default=make_uuid),
    Column('authority_id', types.UnicodeText,
            ForeignKey('user_authority.id', ondelete='CASCADE')),
    Column('dataset_id', types.UnicodeText,
            ForeignKey('package.id', ondelete='CASCADE')),
    Column('created', types.DateTime, default=datetime.datetime.now),
)

mapper(
    UserAuthorityDataset,
    user_authority_dataset_table,
)

def setup():
    metadata.create_all(model.meta.engine)
