# coding: utf8

import json

from ckan import plugins
from ckan.tests import helpers as test_helpers
from ckanext.datagovmk import helpers
from ckan.tests import factories
from ckan.lib.search import rebuild
from ckanext.googleanalytics.dbutil import init_tables as init_tables_ga
from ckanext.datagovmk.model.stats import (get_stats_for_resource,
                                           increment_downloads)
from ckanext.datagovmk.tests.helpers import create_dataset, set_lang
from ckanext.datagovmk.model.user_authority \
    import setup as setup_user_authority_table
from ckanext.datagovmk.model.user_authority_dataset \
    import setup as setup_user_authority_dataset_table
from ckanext.datagovmk.model.most_active_organizations \
    import setup as setup_most_active_organizations_table
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckanext.c3charts.model.featured_charts import setup as setup_featured_charts_table
from ckanext.googleanalytics.dbutil import update_package_visits
from ckanext.datagovmk.commands import fetch_most_active_orgs


class HelpersBase(object):
    def setup(self):
        test_helpers.reset_db()
        init_tables_ga()
        setup_user_authority_table()
        setup_user_authority_dataset_table()
        setup_featured_charts_table()
        setup_most_active_organizations_table()

        rebuild()

        if not plugins.plugin_loaded('c3charts'):
            plugins.load('c3charts')

        if not plugins.plugin_loaded('datagovmk'):
            plugins.load('datagovmk')

        if not plugins.plugin_loaded('scheming_organizations'):
            plugins.load('scheming_organizations')

        if not plugins.plugin_loaded('fluent'):
            plugins.load('fluent')

    @classmethod
    def teardown_class(self):

        if plugins.plugin_loaded('datagovmk'):
            plugins.unload('datagovmk')

        if plugins.plugin_loaded('c3charts'):
            plugins.unload('c3charts')

        if plugins.plugin_loaded('scheming_organizations'):
            plugins.unload('scheming_organizations')

        if plugins.plugin_loaded('fluent'):
            plugins.unload('fluent')


class TestHelpers(HelpersBase, test_helpers.FunctionalTestBase):
    def test_get_recently_updated_datasets(self):
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

    @test_helpers.change_config('ckan.auth.create_unowned_dataset', False)
    def test_get_most_active_organizations(self):
        organization = factories.Organization()
        dataset = factories.Dataset(owner_org=organization['id'])
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com', skip_update_package_stats=True)

        organization2 = factories.Organization()
        dataset1 = factories.Dataset(owner_org=organization2['id'])
        resource1 = factories.Resource(package_id=dataset1['id'], url='http://google.com', skip_update_package_stats=True)
        dataset2 = factories.Dataset(owner_org=organization2['id'])
        resource2 = factories.Resource(package_id=dataset2['id'], url='http://google.com', skip_update_package_stats=True)
        resource3 = factories.Resource(package_id=dataset2['id'], url='http://google.com', skip_update_package_stats=True)

        organization3 = factories.Organization()
        dataset3 = factories.Dataset(owner_org=organization3['id'])
        resource4 = factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
        resource5 = factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
        resource6 = factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
        resource7 = factories.Resource(package_id=dataset3['id'], url='http://google.com', skip_update_package_stats=True)
        dataset4 = factories.Dataset(owner_org=organization3['id'])
        resource7 = factories.Resource(package_id=dataset4['id'], url='http://google.com', skip_update_package_stats=True)

        fetch_most_active_orgs()
        result = helpers.get_most_active_organizations()

        assert len(result) == 3
        assert result[0].org_id == organization3['id']

        resource8 = factories.Resource(package_id=dataset['id'], url='http://google.com', skip_update_package_stats=True)

        fetch_most_active_orgs()
        result = helpers.get_most_active_organizations()

        assert result[0].org_id == organization['id']

        for i in range(10):
            organizationMultiple = factories.Organization()
            create_dataset(owner_org=organizationMultiple['id'])

        fetch_most_active_orgs()
        result = helpers.get_most_active_organizations(limit=7)

        assert len(result) == 7

    def test_get_related_datasets(self):
        dataset = create_dataset(tags=[{'name': 'cat'}])
        dataset2 = create_dataset(tags=[{'name': 'cat'}])

        id = dataset['id']

        result = helpers.get_related_datasets(id)

        assert result[0]['id'] == dataset2['id']

        group = factories.Group()
        dataset = create_dataset(groups=[{'id': group['id']}])
        dataset2 = create_dataset(groups=[{'id': group['id']}])
        dataset3 = create_dataset(groups=[{'id': group['id']}])
        dataset4 = create_dataset(groups=[{'id': group['id']}])

        id = dataset['id']

        result = helpers.get_related_datasets(id)

        assert result[0]['id'] == dataset4['id']

        result = helpers.get_related_datasets(id, limit=2)

        assert len(result) == 2

    def test_get_groups(self):

        groupEmpty = factories.Group()
        result = helpers.get_groups()

        assert len(result) == 0

        group = factories.Group()
        dataset = create_dataset(groups=[{'id': group['id']}])

        group2 = factories.Group()
        dataset2 = create_dataset(groups=[{'id': group2['id']}])
        dataset3 = create_dataset(groups=[{'id': group2['id']}])

        group3 = factories.Group()
        dataset4 = create_dataset(groups=[{'id': group3['id']}])
        dataset5 = create_dataset(groups=[{'id': group3['id']}])
        dataset6 = create_dataset(groups=[{'id': group3['id']}])

        result = helpers.get_groups()

        assert result[0]['id'] == group3['id']

        assert len(result) == 3

    def test_get_resource_stats(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
        resource_id = resource['id']

        increment_downloads(resource_id)
        increment_downloads(resource_id)
        increment_downloads(resource_id)

        result = helpers.get_resource_stats(resource_id)
        assert result['downloads'] == 3

    def test_get_package_total_downloads(self):
        dataset = create_dataset()
        dataset_id = dataset['id']
        resource = factories.Resource(package_id=dataset_id, url='http://google.com')
        resource2 = factories.Resource(package_id=dataset_id, url='http://google.com')

        increment_downloads(resource['id'])
        increment_downloads(resource2['id'])

        result = helpers.get_package_total_downloads(dataset_id)
        assert result == 2

    def test_get_storage_path_for(self):
        result = helpers.get_storage_path_for("pictures")
        assert result == '/tmp/storage/pictures'

    def test_get_user_id(self):
        user = factories.Sysadmin()
        user_id = helpers.get_user_id(user['name'])

        assert user_id == user['id']

    def test_get_last_authority_for_user(self):
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

    def test_translate_field_mk(self):
        data_dict = {
            'title_translated': {
                'mk': 'тест',
                'en': 'test',
            }
        }

        set_lang('mk')
        result = helpers.translate_field(data_dict, 'title')

        assert result == 'тест'

    def test_translate_field_sq(self):
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

    def test_get_org_title_mk(self):
        title_translated = {
            'en': 'title on english',
            'mk': u'наслов на македонски',
            'sq': 'titulli i shqiptar'
        }
        org = factories.Organization(title_translated=title_translated)
        set_lang('mk')
        result = helpers.get_org_title(org['id'])
        assert result == u'наслов на македонски'

    def test_get_org_title_sq(self):
        title_translated = {
            'en': 'title on english',
            'mk': u'наслов на македонски',
            'sq': 'titulli i shqiptar'
        }
        org = factories.Organization(title_translated=title_translated)
        set_lang('sq')
        result = helpers.get_org_title(org['id'])
        assert result == u'titulli i shqiptar'

    def test_get_org_description_mk(self):
        description_translated = {
            'en': 'description on english',
            'mk': u'опис на македонски',
            'sq': 'përshkrimi i shqiptar'
        }
        org = factories.Organization(description_translated=description_translated)
        set_lang('mk')
        result = helpers.get_org_description(org['id'])
        assert result == u'опис на македонски'

    def test_get_org_description_sq(self):
        description_translated = {
            'en': 'description on english',
            'mk': u'опис на македонски',
            'sq': u'përshkrimi i shqiptar'
        }
        org = factories.Organization(description_translated=description_translated)
        set_lang('sq')
        result = helpers.get_org_description(org['id'])
        assert result == u'përshkrimi i shqiptar'

    def test_get_org_title_desc(self):
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

    def test_get_translated(self):
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

    @test_helpers.change_config('ckan.auth.create_unowned_dataset', True)
    def test_get_org_catalog(self):
        org = factories.Organization()
        extras = [{'key': 'org_catalog_enabled', 'value': True}]
        dataset = factories.Dataset(owner_org=org['id'], extras=extras)
        result = helpers.get_org_catalog(org['id'])

        assert type(result) is dict
        assert result.get('id') == dataset.get('id')

    def test_get_catalog_count(self):
        org = factories.Organization()
        extras = [{'key': 'org_catalog_enabled', 'value': True}]
        dataset = factories.Dataset(owner_org=org['id'], extras=extras)
        dataset1 = factories.Dataset(owner_org=org['id'], extras=extras)

        result = helpers.get_catalog_count('')
        assert result == 2

    def test_get_dataset_stats(self):
        dataset = create_dataset()
        update_package_visits(dataset.get('id'), 10, 28)
        result = helpers.get_dataset_stats(dataset.get('id'))

        assert result.get('id') == dataset.get('id')
        assert result.get('visits_recently') == 10
        assert result.get('visits_ever') == 28

    def test_get_site_statistics(self):
        group = factories.Group()
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'])
        dataset1 = factories.Dataset(owner_org=org['id'])

        stats = helpers.get_site_statistics('')

        assert stats.get('dataset_count') == 2
        assert stats.get('organization_count') == 1
        assert stats.get('group_count') == 1
