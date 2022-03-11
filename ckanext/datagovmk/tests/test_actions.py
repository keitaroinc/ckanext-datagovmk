# coding: utf8

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
import cgi
from distutils.command.upload import upload
import pytest
from io import StringIO, BytesIO

from flask import request
import requests

from ckan import model
from ckan import plugins
from ckan.plugins import toolkit
from ckan.tests import helpers as test_helpers
from ckan.tests import factories
from ckan.common import config

from ckanext.datagovmk import actions
from ckanext.datagovmk.tests.helpers import create_dataset
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckanext.datagovmk.model.stats import increment_downloads
from ckanext.datagovmk.tests import factories as dgm_factories
from ckanext.datagovmk.tests.fixtures import dgm_setup


class User(object):
    def __init__(self, id):
        self.id = id

class FakeFileStorage(cgi.FieldStorage):
    def __init__(self, fp, filename):
        self.file = fp
        self.filename = filename
        self.name = 'upload'


def _create_fs(mimetype, content):
    fs = cgi.FieldStorage()
    content = content.encode('utf-8')
    fs.file = BytesIO(content)
    fs.type = mimetype
    fs.filename = 'test.json'
    fs.name = 'upload'
    return fs


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_prepare_zip_resources():
    user = dgm_factories.User()
    org = factories.Organization()
    dataset = dgm_factories.Dataset(user=user, owner_org=org['id'])
    resource = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/posts')
    resource1 = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/comments')
    resource_ids = [resource.get('id'), resource1.get('id')]
    data_dict = {'resources': resource_ids}
    result = actions.prepare_zip_resources({}, data_dict)
    assert 'zip_id' in result


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_add_spatial_data():
    package_create = toolkit.get_action('package_create')
    package_update = toolkit.get_action('package_update')
    data_dict = {
        'spatial_uri': 'MK-03',
        'name': "dataset",
        'add_dataset_agreement': 'yes',
        'title_translated-mk': 'title',
        'notes_translated-mk': 'notes',
        'maintainer': 'John'
    }
    spatial_data = actions.add_spatial_data(package_create)
    sysadmin = factories.Sysadmin()
    data = {
        'user_id': sysadmin.get('id'),
        'authority_file': 'test.png',
        'authority_type': 'general'
    }

    userAuthority = UserAuthority(**data)
    userAuthority.save()

    user = User(sysadmin.get('id'))
    result = spatial_data({'user': sysadmin.get(
        'name'), 'auth_user_obj': user}, data_dict)
    assert result.get('extras')[0].get('key') == 'spatial'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_resource_create_invalid_url():
    dataset = create_dataset()

    with pytest.raises(toolkit.ValidationError, match=r"Invalid URL"):
        factories.Resource(package_id=dataset['id'], url='www.random.com')


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_resource_create_valid_url():
    dataset = create_dataset()
    factories.Resource(package_id=dataset['id'], url='http://google.com')


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_resource_create_uploaded_file():
    dataset = create_dataset()
    content = ('''
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    ''')
    test_file = _create_fs('application/json', content)
    resource = factories.Resource(
        package_id=dataset['id'], upload=test_file)
    
    content_2 = ('''
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    ''')
    test_file_1 = _create_fs('application/json', content_2)

    with pytest.raises(toolkit.ValidationError) as cm:
        resource = factories.Resource(
            package_id=dataset['id'], upload=test_file_1)
    assert cm.value.error_dict == {u'message': ['Resource already exists']}


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_resource_update_invalid_url():
    dataset = create_dataset()
    resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
    data_dict = {'id': resource['id'], 'url': "www.invalidurl.com"}
    user = factories.Sysadmin()
    with pytest.raises(toolkit.ValidationError, match=r"Invalid URL"):
        result = actions.resource_update({'user': user.get('name'), 'model': model}, data_dict)


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_resource_update_valid_url():
    dataset = create_dataset()
    resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
    data_dict = {'id': resource['id'], 'url': "http://yahoo.com"}
    user = factories.Sysadmin()
    actions.resource_update({'user': user.get('name'), 'model': model}, data_dict)


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_resource_delete():
    dataset = create_dataset()
    resource = factories.Resource(package_id=dataset['id'], url="http://yahoo.com")

    action = toolkit.get_action('resource_delete')
    user = factories.Sysadmin()
    context = {
        'user': user.get('name')
    }
    data_dict = {
        'id': resource['id']
    }
    result = actions.resource_delete(action, context, data_dict)

    assert result is None

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_start_script_valid_script_name():
    sysadmin = factories.Sysadmin()
    context = {'user': sysadmin.get('name')}
    data_dict = {'name': 'report'}

    result = actions.start_script(context, data_dict)

    assert result == 'Script was successfully executed.'
        
@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_start_script_invalid_script_name():
    sysadmin = factories.Sysadmin()
    context = {'user': sysadmin.get('name')}
    data_dict = {'name': 'test'}

    with pytest.raises(toolkit.ValidationError) as cm:
        result = actions.start_script(context, data_dict)

    assert cm.value.error_dict == \
        {'name': u'No script was found for the provided name'}
    
# @pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
# def test_user_create():
#     user = factories.Sysadmin()
#     context = {'model': model, 'session': model.Session, 'user': user.get('name')}
#     data_dict = {
#         'name': 'test',
#         'email': 'test@test.com',
#         'password': '123456789'
#     }
#     test_helpers.call_action('user_create', context=context, **data_dict)

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_user_update():
    user = factories.Sysadmin()
    context = {
        'user': user['name'],
        'model': model,
        'session': model.Session
    }
    data_dict = {
        'authority_file_url': 'test.png',
        'id': user['id'],
        'fullname': 'NewName',
        'email': 'example@example.com'
    }
    result = actions.user_update(context, data_dict)
    assert result['fullname'] == 'NewName'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_user_activity_list():
    user = factories.Sysadmin()
    context = {
        'user': user['name'],
        'model': model,
        'session': model.Session
    }
    data_dict = {
        'id': user['id']
    }

    result = actions.user_activity_list(context, data_dict)
    assert result == []

    data_dict = {
        'authority_file_url': 'test.png',
        'id': user['id'],
        'fullname': 'NewName',
        'email': 'example@example.com'
    }
    actions.user_update(context, data_dict)
    result = actions.user_activity_list(context, data_dict)

    assert len(result) == 1

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_dashboard_activity_list():
    user = factories.Sysadmin()
    context = {
        'user': user['name'],
        'model': model,
        'session': model.Session
    }
    data_dict = {
        'id': user['id']
    }

    result = actions.dashboard_activity_list(context, data_dict)
    assert result == []

    data_dict = {
        'authority_file_url': 'test.png',
        'id': user['id'],
        'fullname': 'NewName',
        'email': 'example@example.com'
    }
    actions.user_update(context, data_dict)
    result = actions.dashboard_activity_list(context, data_dict)

    assert len(result) == 1

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_package_search():
    title_translated = {
        'en': 'title on english',
        'mk': u'наслов на македонски',
        'sq': 'titulli i shqiptar'
    }
    dataset = create_dataset(
        title_translated=title_translated,
        name='testtranstitle'
    )

    data_dict = {
        'fq': 'name:testtranstitle'
    }
    request.environ['CKAN_LANG'] = 'mk'
    result = test_helpers.call_action('package_search', **data_dict)
    assert result.get('results')[0]['title'] == u'наслов на македонски'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_package_stats():
    dataset = create_dataset()
    content = ('''
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    ''')
    test_file = _create_fs('application/json', content)

    resource = factories.Resource(
        package_id=dataset['id'], url='http://www.google.com', upload=test_file)
    resource2 = factories.Resource(
        package_id=dataset['id'], url='http://www.yahoo.com')

    increment_downloads(resource['id'])
    increment_downloads(resource['id'])
    increment_downloads(resource2['id'])

    result = actions.get_package_stats(dataset['id'])

    assert result['file_size'] == 605
    assert result['total_downloads'] == 3


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_increment_downloads_for_resource():
    dataset = create_dataset()
    resource = factories.Resource(package_id=dataset.get('id'), url='http://www.google.com')
    result = actions.increment_downloads_for_resource({}, {'resource_id': resource['id']})
    assert result == 'success'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_resource_show_mk():
    dataset = create_dataset()
    data_dict = {
        'package_id': dataset.get('id'),
        'url': 'http://www.google.com',
        'name_translated': {
            'mk': 'name mk',
            'en': 'name en',
            'sq': 'name sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        }
    }
    resource = factories.Resource(**data_dict)
    request.environ['CKAN_LANG'] = 'mk'
    result = test_helpers.call_action('resource_show', id=resource.get('id'))
    assert result.get('name') == 'name mk'
    assert result.get('description') == 'description mk'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_resource_show_sq():
    dataset = create_dataset()
    data_dict = {
        'package_id': dataset.get('id'),
        'url': 'http://www.google.com',
        'name_translated': {
            'mk': 'name mk',
            'en': 'name en',
            'sq': 'name sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        }
    }
    resource = factories.Resource(**data_dict)
    request.environ['CKAN_LANG'] = 'sq'
    result = test_helpers.call_action('resource_show', id=resource.get('id'))
    assert result.get('name') == 'name sq'
    assert result.get('description') == 'description sq'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_organization_show_mk():
    data_dict = {
        'title_translated': {
            'mk': 'title mk',
            'en': 'title en',
            'sq': 'title sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        }
    }
    org = factories.Organization(**data_dict)
    request.environ['CKAN_LANG'] = 'mk'
    result = test_helpers.call_action('organization_show', id=org.get('id'))
    assert result.get('title') == 'title mk'
    assert result.get('display_name') == 'title mk'
    assert result.get('description') == 'description mk'

@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_organization_show_sq():
    data_dict = {
        'title_translated': {
            'mk': 'title mk',
            'en': 'title en',
            'sq': 'title sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        }
    }
    org = factories.Organization(**data_dict)
    request.environ['CKAN_LANG'] = 'sq'
    result = test_helpers.call_action('organization_show', id=org.get('id'))
    assert result.get('title') == 'title sq'
    assert result.get('display_name') == 'title sq'
    assert result.get('description') == 'description sq'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_group_show_mk():
    data_dict = {
        'title_translated': {
            'mk': 'title mk',
            'en': 'title en',
            'sq': 'title sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        },
        'type': 'group'
    }
    group = factories.Group(**data_dict)
    request.environ['CKAN_LANG'] = 'mk'
    result = test_helpers.call_action('group_show', id=group.get('id'))
    assert result.get('title') == 'title mk'
    assert result.get('display_name') == 'title mk'
    assert result.get('description') == 'description mk'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_group_show_sq():
    data_dict = {
        'title_translated': {
            'mk': 'title mk',
            'en': 'title en',
            'sq': 'title sq'
        },
        'description_translated': {
            'mk': 'description mk',
            'en': 'description en',
            'sq': 'description sq'
        },
        'type': 'group',
    }
    org = factories.Group(**data_dict)
    request.environ['CKAN_LANG'] = 'sq'
    result = test_helpers.call_action('group_show', id=org.get('id'))
    assert result.get('title') == 'title sq'
    assert result.get('display_name') == 'title sq'
    assert result.get('description') == 'description sq'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_get_related_datasets():
    dataset = create_dataset(tags=[{'name': 'cat'}])
    dataset2 = create_dataset(tags=[{'name': 'cat'}])

    id = dataset['id']

    result = actions.get_related_datasets({}, {'id': id})

    assert result[0]['id'] == dataset2['id']

    group = factories.Group()
    dataset = create_dataset(groups=[{'id': group['id']}])
    dataset2 = create_dataset(groups=[{'id': group['id']}])
    dataset3 = create_dataset(groups=[{'id': group['id']}])
    dataset4 = create_dataset(groups=[{'id': group['id']}])

    id = dataset['id']

    result = actions.get_related_datasets({}, {'id': id})

    assert result[0]['id'] == dataset4['id']

    result = actions.get_related_datasets({}, {'id': id, 'limit': 2})

    assert len(result) == 2


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_update_package_stats():
    dataset = create_dataset()
    content = ('''
    "info": {
        "title": "BC Data Catalogue API",
        "description": "This API provides information about datasets in the BC Data Catalogue.",
        "termsOfService": "http://www.data.gov.bc.ca/local/dbc/docs/license/API_Terms_of_Use.pdf",
        "contact": {
            "name": "Data BC",
            "url": "http://data.gov.bc.ca/",
            "email": ""
        },
        "license": {
            "name": "Open Government License - British Columbia",
            "url": "http://www.data.gov.bc.ca/local/dbc/docs/license/OGL-vbc2.0.pdf"
        },
        "version": "3.0.0"
    }
    ''')
    test_file = _create_fs('application/json', content)
    resource = factories.Resource(
        package_id=dataset['id'], url='http://www.google.com', upload=test_file)

    increment_downloads(resource['id'])
    increment_downloads(resource['id'])

    actions.update_package_stats(dataset['id'])

    solr_base_url = config['solr_url']
    url = '{0}/select?q=*:*&fq=id:{1}&wt=json'.format(solr_base_url, dataset['id'])

    result = requests.get(url)
    response = result.json().get('response')

    assert response.get('numFound') == 1
    assert response.get('docs')[0].get('extras_total_downloads') == '000000000000000000000002'
    assert response.get('docs')[0].get('extras_file_size') == '000000000000000000000605'
