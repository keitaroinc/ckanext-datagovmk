from ckan import plugins
from ckan.plugins import toolkit
from ckan.tests import helpers as test_helpers
from ckanext.datagovmk import actions
from ckan.tests import factories
from ckan.lib.search import rebuild
from nose.tools import assert_raises
from ckan import model
import cgi
import StringIO
from ckanext.googleanalytics.dbutil import init_tables as init_tables_ga
from ckanext.datagovmk.tests.helpers import create_dataset
from ckanext.datagovmk.model.user_authority import UserAuthority


class User(object):
    def __init__(self, id):
        self.id = id


class FakeFileStorage(cgi.FieldStorage):
    def __init__(self, fp, filename):
        self.file = fp
        self.filename = filename
        self.name = 'upload'


class ActionsBase(object):
    def setup(self):
        test_helpers.reset_db()
        init_tables_ga()
        rebuild()

        if not plugins.plugin_loaded('datagovmk'):
            plugins.load('datagovmk')

        if not plugins.plugin_loaded('mk_dcatap'):
            plugins.load('mk_dcatap')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('datagovmk'):
            plugins.unload('datagovmk')
        
        if plugins.plugin_loaded('mk_dcatap'):
            plugins.unload('mk_dcatap')


class TestActions(ActionsBase):
    def test_prepare_zip_resources(self):
        dataset = create_dataset()    
        resource = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/posts')
        resource1 = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/comments')
        resource_ids = [resource.get('id'), resource1.get('id')]
        data_dict = {'resources': resource_ids}
        result = actions.prepare_zip_resources({}, data_dict)
        assert 'zip_id' in result

    # def test_download_zip(self):
    #     dataset = create_dataset()    
    #     resource = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/posts')
    #     resource1 = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/comments')
    #     resource_ids = [resource.get('id'), resource1.get('id')]
    #     data_dict = {'resources': resource_ids}
    #     result = actions.prepare_zip_resources({}, data_dict)
    #     actions.download_zip({}, {'id': result.get('zip_id')})

    def test_add_spatial_data(self):
        package_create = toolkit.get_action('package_create')
        package_update = toolkit.get_action('package_update')
        data_dict = {'spatial_uri': 'MK-03', 'name': "dataset", 'add_dataset_agreement': 'yes'}
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
        result = spatial_data({'user': 'default', 'auth_user_obj': user}, data_dict)
        assert result.get('extras')[0].get('key') == 'spatial'

    def test_resource_create_invalid_url(self):
        dataset = create_dataset()
        with assert_raises(toolkit.ValidationError) as cm:
            resource = factories.Resource(package_id=dataset['id'], url='http://brmbrm.com')
        assert cm.exception.error_summary == {u'Message': u'Invalid URL'}

    def test_resource_create_valid_url(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com')

    def test_resource_create_uploaded_file(self):
        dataset = create_dataset()
        test_file = StringIO.StringIO()
        test_file.write('''
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
        test_resource = FakeFileStorage(test_file, 'test.json')
        resource = factories.Resource(package_id=dataset['id'], upload=test_resource)
        test_file = StringIO.StringIO()
        test_file.write('''
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
        test_resource = FakeFileStorage(test_file, 'test.json')
        with assert_raises(toolkit.ValidationError) as cm:
            resource = factories.Resource(package_id=dataset['id'], upload=test_resource)
        assert cm.exception.error_summary == {u'Message': u'Resource already exists'}

    def test_resource_update_invalid_url(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
        data_dict = {'id': resource['id'], 'url': "http://brmbrm.com"}
        user = factories.Sysadmin()
        with assert_raises(toolkit.ValidationError) as cm:
            result = actions.resource_update({'user': user.get('name'), 'model': model}, data_dict)
        assert cm.exception.error_summary == {u'Message': u'Invalid URL'}

    def test_resource_update_valid_url(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset['id'], url='http://google.com')
        data_dict = {'id': resource['id'], 'url': "http://yahoo.com"}
        user = factories.Sysadmin()
        result = actions.resource_update({'user': user.get('name'), 'model': model}, data_dict)

    def test_resource_update_uploaded_file(self):
        dataset = create_dataset()
        test_file = StringIO.StringIO()
        test_file.write('''
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
        test_resource = FakeFileStorage(test_file, 'test.json')
        resource = factories.Resource(package_id=dataset['id'], upload=test_resource)
        test_file = StringIO.StringIO()
        test_file.write('''
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
        test_resource = FakeFileStorage(test_file, 'test.json')
        with assert_raises(toolkit.ValidationError) as cm:
            data_dict = {'id': resource['id'], 'upload': test_resource}
            user = factories.Sysadmin()
            result = actions.resource_update({'user': user.get('name'), 'model': model}, data_dict)
        assert cm.exception.error_summary == {u'Message': u'Resource already exists'}