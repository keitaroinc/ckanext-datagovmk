from ckan import plugins
from ckan.tests import helpers as test_helpers
from ckanext.datagovmk import helpers
from ckan.tests import factories
from ckan.lib.search import rebuild
from ckanext.datagovmk.model.stats import (get_stats_for_resource,
                                           increment_downloads)

class HelpersBase(object):
    @classmethod
    def setup_class(self):
        if not plugins.plugin_loaded('datagovmk'):
            plugins.load('datagovmk')

    def setup(self):
        test_helpers.reset_db()
        rebuild()

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('datagovmk'):
            plugins.unload('datagovmk')


class TestHelpers(HelpersBase):
    def test_get_recently_updated_datasets(self):
        factories.Dataset()
        factories.Dataset()
        factories.Dataset()
        dataset = factories.Dataset()    
        
        result = helpers.get_recently_updated_datasets()
        
        assert len(result) == 4
        assert result[0]['id'] == dataset['id']

        result = helpers.get_recently_updated_datasets(limit=2)

        assert len(result) == 2 
        assert result[0]['id'] == dataset['id']
        

    def test_get_most_active_organizations(self):
        organization = factories.Organization()
        factories.Dataset(owner_org=organization['id'])  
        organization2 = factories.Organization()
        factories.Dataset(owner_org=organization2['id'])  
        factories.Dataset(owner_org=organization2['id'])

        result = helpers.get_most_active_organizations()
        
        assert len(result) == 2
        assert result[0]['id'] == organization2['id']

        for i in range(10):
            organization = factories.Organization()
            factories.Dataset(owner_org=organization['id'])

        result = helpers.get_most_active_organizations(limit=7)

        assert len(result) == 7

    def test_get_related_datasets(self):
        dataset = factories.Dataset(tags=[{'name': 'cat'}])
        dataset2 = factories.Dataset(tags=[{'name': 'cat'}])
        
        id = dataset['id']
        
        result = helpers.get_related_datasets(id)

        assert result[0]['id'] == dataset2['id']

        group = factories.Group()
        dataset = factories.Dataset(groups=[{'id': group['id']}])
        dataset2 = factories.Dataset(groups=[{'id': group['id']}])
        dataset3 = factories.Dataset(groups=[{'id': group['id']}])
        dataset4 = factories.Dataset(groups=[{'id': group['id']}])
        
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
        dataset = factories.Dataset(groups=[{'id': group['id']}])
                
        group2 = factories.Group()
        dataset2 = factories.Dataset(groups=[{'id': group2['id']}])
        dataset3 = factories.Dataset(groups=[{'id': group2['id']}])

        group3 = factories.Group()
        dataset4 = factories.Dataset(groups=[{'id': group3['id']}])
        dataset5 = factories.Dataset(groups=[{'id': group3['id']}])
        dataset6 = factories.Dataset(groups=[{'id': group3['id']}])
        
        result = helpers.get_groups()

        assert result[0]['id'] == group3['id']

        assert len(result) == 3

    def test_get_resource_stats(self):
        dataset = factories.Dataset()
        resource = factories.Resource(package_id=dataset['id'])
        resource_id = resource['id']

        increment_downloads(resource_id)
        increment_downloads(resource_id)
        increment_downloads(resource_id)
        
        result = helpers.get_resource_stats(resource_id)
        assert result['downloads'] == 3

    def test_get_package_total_downloads(self):
        dataset = factories.Dataset()
        dataset_id = dataset['id']        
        resource = factories.Resource(package_id=dataset_id)
        resource2 = factories.Resource(package_id=dataset_id)
        
        increment_downloads(resource['id'])
        increment_downloads(resource2['id'])
        
        result = helpers.get_package_total_downloads(dataset_id)
        assert result == 2