from ckan import plugins
from ckan.tests import helpers as test_helpers
from ckanext.datagovmk import helpers
from ckan.tests import factories
from ckan.lib.search import rebuild
from ckanext.googleanalytics.dbutil import init_tables as init_tables_ga
from ckanext.datagovmk.model.stats import (get_stats_for_resource,
                                           increment_downloads)
from ckanext.datagovmk.tests.helpers import create_dataset


class HelpersBase(object):
    def setup(self):
        test_helpers.reset_db()
        init_tables_ga()
        rebuild()

        if not plugins.plugin_loaded('datagovmk'):
            plugins.load('datagovmk')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('datagovmk'):
            plugins.unload('datagovmk')


class TestHelpers(HelpersBase):
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
        
    def test_get_most_active_organizations(self):
        organization = factories.Organization()
        dataset = create_dataset(owner_org=organization['id'])
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
        
        organization2 = factories.Organization()
        dataset1 = create_dataset(owner_org=organization2['id'])  
        resource1 = factories.Resource(package_id=dataset1['id'], url='http://google.com')
        dataset2 = create_dataset(owner_org=organization2['id'])
        resource2 = factories.Resource(package_id=dataset2['id'], url='http://google.com')
        resource3 = factories.Resource(package_id=dataset2['id'], url='http://google.com')

        organization3 = factories.Organization()
        dataset3 = create_dataset(owner_org=organization3['id'])
        resource4 = factories.Resource(package_id=dataset3['id'], url='http://google.com')
        resource5 = factories.Resource(package_id=dataset3['id'], url='http://google.com')
        resource6 = factories.Resource(package_id=dataset3['id'], url='http://google.com')
        resource7 = factories.Resource(package_id=dataset3['id'], url='http://google.com')
        dataset4 = create_dataset(owner_org=organization3['id'])
        resource7 = factories.Resource(package_id=dataset4['id'], url='http://google.com')

        result = helpers.get_most_active_organizations()
        
        assert len(result) == 3
        assert result[0]['id'] == organization3['id']
        resource8 = factories.Resource(package_id=dataset['id'], url='http://google.com')
        result = helpers.get_most_active_organizations()
        assert result[0]['id'] == organization['id']

        for i in range(10):
            organizationMultiple = factories.Organization()
            create_dataset(owner_org=organizationMultiple['id'])

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