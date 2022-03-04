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

import json
import pytest

from flask import request

from ckan.tests import helpers as test_helpers
from ckanext.datagovmk import helpers
from ckan.tests import factories

from ckanext.datagovmk.model.stats import increment_downloads
from ckanext.datagovmk.tests.helpers import create_dataset, set_lang
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckanext.googleanalytics.dbutil import update_package_visits
from ckanext.datagovmk.commands import fetch_most_active_orgs
from ckanext.datagovmk.tests import factories as dgm_factories
from ckanext.datagovmk.tests.fixtures import dgm_setup


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_recently_updated_datasets():
    create_dataset()
    create_dataset()
    create_dataset()
    dataset = create_dataset()

    result = helpers.get_recently_updated_datasets()

    assert len(result) == 4
    assert result[0]['id'] == dataset['id']

    result = helpers.get_recently_updated_datasets(limit=2)

    assert len(result) == 2
    assert result[0]['id'] == dataset['id']


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
@test_helpers.change_config('ckan.auth.create_unowned_dataset', False)
def test_get_most_active_organizations():
    user = dgm_factories.User()
    organization = factories.Organization()
    dataset = dgm_factories.Dataset(
        user=user, owner_org=organization['id'])
    factories.Resource(package_id=dataset['id'], url='http://google.com', skip_update_package_stats=True)

    organization2 = factories.Organization()
    dataset1 = dgm_factories.Dataset(
        user=user, owner_org=organization2['id'])
    factories.Resource(package_id=dataset1['id'], url='http://google.com', skip_update_package_stats=True)
    dataset2 = dgm_factories.Dataset(
        user=user, owner_org=organization2['id'])
    factories.Resource(package_id=dataset2['id'], url='http://google.com', skip_update_package_stats=True)
    factories.Resource(package_id=dataset2['id'], url='http://google.com', skip_update_package_stats=True)

    organization3 = factories.Organization()
    dataset3 = dgm_factories.Dataset(
        user=user, owner_org=organization3['id'])
    factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
    factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
    factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
    factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
    dataset4 = dgm_factories.Dataset(user=user, owner_org=organization3['id'])
    factories.Resource(package_id=dataset4['id'], url='http://google.com', skip_update_package_stats=True)

    fetch_most_active_orgs()
    result = helpers.get_most_active_organizations()

    assert len(result) == 3
    assert result[0].org_id == organization3['id']

    factories.Resource(package_id=dataset['id'], url='http://google.com', skip_update_package_stats=True)

    fetch_most_active_orgs()
    result = helpers.get_most_active_organizations()

    assert result[0].org_id == organization['id']

    for i in range(10):
        organizationMultiple = factories.Organization()
        create_dataset(owner_org=organizationMultiple['id'])

    fetch_most_active_orgs()
    result = helpers.get_most_active_organizations(limit=7)

    assert len(result) == 7


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_get_related_datasets():
    dataset = create_dataset(tags=[{'name': 'cat'}])
    dataset2 = create_dataset(tags=[{'name': 'cat'}])

    id = dataset['id']

    result = helpers.get_related_datasets(id)

    assert result[0]['id'] == dataset2['id']

    group = factories.Group()
    dataset = create_dataset(groups=[{'id': group['id']}])
    dataset2 = create_dataset(groups=[{'id': group['id']}])
    create_dataset(groups=[{'id': group['id']}])
    dataset4 = create_dataset(groups=[{'id': group['id']}])

    id = dataset['id']

    result = helpers.get_related_datasets(id)

    assert result[0]['id'] == dataset4['id']

    result = helpers.get_related_datasets(id, limit=2)

    assert len(result) == 2


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_groups():

    factories.Group()
    result = helpers.get_groups()

    assert len(result) == 0

    group = factories.Group()
    create_dataset(groups=[{'id': group['id']}])

    group2 = factories.Group()
    create_dataset(groups=[{'id': group2['id']}])
    create_dataset(groups=[{'id': group2['id']}])

    group3 = factories.Group()
    create_dataset(groups=[{'id': group3['id']}])
    create_dataset(groups=[{'id': group3['id']}])
    create_dataset(groups=[{'id': group3['id']}])

    result = helpers.get_groups()

    assert result[0]['id'] == group3['id']

    assert len(result) == 3


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_resource_stats():
    dataset = create_dataset()
    resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
    resource_id = resource['id']

    increment_downloads(resource_id)
    increment_downloads(resource_id)
    increment_downloads(resource_id)

    result = helpers.get_resource_stats(resource_id)
    assert result['downloads'] == 3


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_package_total_downloads():
    dataset = create_dataset()
    dataset_id = dataset['id']
    resource = factories.Resource(package_id=dataset_id, url='http://google.com')
    resource2 = factories.Resource(package_id=dataset_id, url='http://google.com')

    increment_downloads(resource['id'])
    increment_downloads(resource2['id'])

    result = helpers.get_package_total_downloads(dataset_id)
    assert result == 2


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_storage_path_for():
    result = helpers.get_storage_path_for("pictures")
    assert result == '/tmp/storage/pictures'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_user_id():
    user = factories.Sysadmin()
    user_id = helpers.get_user_id(user['name'])

    assert user_id == user['id']


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_last_authority_for_user():
    sysadmin = factories.Sysadmin()

    data = {
        'user_id': sysadmin.get('id'),
        'authority_file': 'test.png',
        'authority_type': 'general'
    }

    userAuthority = UserAuthority(**data)
    userAuthority.save()

    last_authority = helpers.get_last_authority_for_user('general', sysadmin['id'])

    assert last_authority.authority_file == 'test.png'
    assert last_authority.authority_type == 'general'

    data = {
        'user_id': sysadmin.get('id'),
        'authority_file': 'test2.png',
        'authority_type': 'general'
    }

    userAuthority = UserAuthority(**data)
    userAuthority.save()

    last_authority = helpers.get_last_authority_for_user('general', sysadmin['id'])

    assert last_authority.authority_file == 'test2.png'
    assert last_authority.authority_type == 'general'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_translate_field_mk():
    data_dict = {
        'title_translated': {
            'mk': 'тест',
            'en': 'test',
        }
    }

    set_lang('mk')
    result = helpers.translate_field(data_dict, 'title')

    assert result == 'тест'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_translate_field_sq():
    data_dict = {
        'title_translated': {
            'mk': 'тест',
            'en': 'test',
            'sq': 'provë'
        }
    }

    set_lang('sq')
    result = helpers.translate_field(data_dict, 'title')

    assert result == 'provë'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_org_title_mk():
    title_translated = {
        'en': 'title on english',
        'mk': u'наслов на македонски',
        'sq': 'titulli i shqiptar'
    }
    org = factories.Organization(title_translated=title_translated)
    set_lang('mk')
    result = helpers.get_org_title(org['id'])
    assert result == u'наслов на македонски'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_org_title_sq():
    title_translated = {
        'en': 'title on english',
        'mk': u'наслов на македонски',
        'sq': 'titulli i shqiptar'
    }
    org = factories.Organization(title_translated=title_translated)
    set_lang('sq')
    result = helpers.get_org_title(org['id'])
    assert result == u'titulli i shqiptar'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_org_description_mk():
    description_translated = {
        'en': 'description on english',
        'mk': u'опис на македонски',
        'sq': 'përshkrimi i shqiptar'
    }
    org = factories.Organization(description_translated=description_translated)
    set_lang('mk')
    result = helpers.get_org_description(org['id'])
    assert result == u'опис на македонски'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_org_description_sq():
    description_translated = {
        'en': 'description on english',
        'mk': u'опис на македонски',
        'sq': u'përshkrimi i shqiptar'
    }
    org = factories.Organization(description_translated=description_translated)
    set_lang('sq')
    result = helpers.get_org_description(org['id'])
    assert result == u'përshkrimi i shqiptar'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_org_title_desc():
    title_translated = {
        'en': 'title on english',
        'mk': u'наслов на македонски',
        'sq': 'titulli i shqiptar'
    }

    description_translated = {
        'en': 'description on english',
        'mk': u'опис на македонски',
        'sq': u'përshkrimi i shqiptar'
    }

    org = factories.Organization(title_translated=title_translated, description_translated=description_translated)

    set_lang('mk')
    title, desc = helpers.get_org_title_desc(org)
    assert title == u'наслов на македонски'
    assert desc == u'опис на македонски'

    set_lang('sq')
    title, desc = helpers.get_org_title_desc(org)
    assert title == u'titulli i shqiptar'
    assert desc == u'përshkrimi i shqiptar'

    set_lang('en')
    title, desc = helpers.get_org_title_desc(org)
    assert title == u'title on english'
    assert desc == u'description on english'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_translated():
    title_translated = {
        'en': 'title on english',
        'mk': u'наслов на македонски',
        'sq': 'titulli i shqiptar'
    }

    json_str = json.dumps(title_translated)

    set_lang('mk')
    t = helpers.get_translated(json_str)
    assert t == u'наслов на македонски'

    set_lang('en')
    t = helpers.get_translated(json_str)
    assert t == 'title on english'

    set_lang('sq')
    t = helpers.get_translated(json_str)
    assert t == 'titulli i shqiptar'


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
@test_helpers.change_config('ckan.auth.create_unowned_dataset', True)
def test_get_org_catalog():
    user = dgm_factories.User()
    org = factories.Organization()
    dataset = dgm_factories.Dataset(
        user=user, owner_org=org['id'], org_catalog_enabled='true')
    result = helpers.get_org_catalog(org['id'])

    assert type(result) is dict
    assert result.get('id') == dataset.get('id')


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_catalog_count():
    user = dgm_factories.User()
    org = factories.Organization()
    org1 = factories.Organization()
    dgm_factories.Dataset(
        user=user, owner_org=org['id'], org_catalog_enabled='true')
    dgm_factories.Dataset(
        user=user, owner_org=org1['id'], org_catalog_enabled='true')

    result = helpers.get_catalog_count('')
    assert result == 2


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins")
def test_get_dataset_stats():
    dataset = create_dataset()
    update_package_visits(dataset.get('id'), 10, 28)
    result = helpers.get_dataset_stats(dataset.get('id'))

    assert result.get('id') == dataset.get('id')
    assert result.get('visits_recently') == 10
    assert result.get('visits_ever') == 28


@pytest.mark.usefixtures("clean_db", "dgm_setup", "with_plugins", "with_request_context")
def test_get_site_statistics():
    user = dgm_factories.User()
    factories.Group()
    org = factories.Organization()
    dgm_factories.Dataset(user=user, owner_org=org['id'])
    dgm_factories.Dataset(user=user, owner_org=org['id'])

    request.environ['CKAN_LANG'] = 'en'
    stats = helpers.get_site_statistics(user['id'])

    assert stats['dataset_count'] == 2
    assert stats['organization_count'] == 1
    assert stats.get('group_count') == 1
