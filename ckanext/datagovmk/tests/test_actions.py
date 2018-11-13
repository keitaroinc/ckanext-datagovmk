# coding: utf8

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
from ckanext.datagovmk.tests.helpers import create_dataset, set_lang, mock_pylons
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckanext.datagovmk.model.user_authority \
    import setup as setup_user_authority_table
from ckanext.datagovmk.model.user_authority_dataset \
    import setup as setup_user_authority_dataset_table
from ckanext.c3charts.model.featured_charts import setup as setup_featured_charts_table
from ckanext.datagovmk.model.stats import increment_downloads
import requests
from ckan.common import config
import pylons


class User(object):
    def __init__(self, id):
        self.id = id

class FakeFileStorage(cgi.FieldStorage):
    def __init__(self, fp, filename):
        self.file = fp
        self.filename = filename
        self.name = 'upload'


class ActionsBase(test_helpers.FunctionalTestBase):
    def setup(self):
        # test_helpers.reset_db()
        init_tables_ga()
        setup_user_authority_table()
        setup_user_authority_dataset_table()
        setup_featured_charts_table()
        rebuild()

        if not plugins.plugin_loaded('c3charts'):
            plugins.load('c3charts')

        if not plugins.plugin_loaded('datagovmk'):
            plugins.load('datagovmk')

        if not plugins.plugin_loaded('scheming_groups'):
            plugins.load('scheming_groups')

        if not plugins.plugin_loaded('scheming_organizations'):
            plugins.load('scheming_organizations')

        if not plugins.plugin_loaded('scheming_datasets'):
            plugins.load('scheming_datasets')

        if not plugins.plugin_loaded('fluent'):
            plugins.load('fluent')

        if not plugins.plugin_loaded('mk_dcatap'):
            plugins.load('mk_dcatap')

        if not plugins.plugin_loaded('validation'):
            plugins.load('validation')

        if not plugins.plugin_loaded('pages'):
            plugins.load('pages')

        if not plugins.plugin_loaded('repeating'):
            plugins.load('repeating')

    @classmethod
    def teardown_class(self):
        if plugins.plugin_loaded('datagovmk'):
            plugins.unload('datagovmk')

        if plugins.plugin_loaded('c3charts'):
            plugins.unload('c3charts')

        if plugins.plugin_loaded('scheming_organizations'):
            plugins.unload('scheming_organizations')

        if plugins.plugin_loaded('scheming_groups'):
            plugins.unload('scheming_groups')

        if plugins.plugin_loaded('scheming_datasets'):
            plugins.unload('scheming_datasets')

        if plugins.plugin_loaded('fluent'):
            plugins.unload('fluent')

        if plugins.plugin_loaded('mk_dcatap'):
            plugins.unload('mk_dcatap')

        if plugins.plugin_loaded('validation'):
            plugins.unload('validation')

        if plugins.plugin_loaded('pages'):
            plugins.unload('pages')

        if plugins.plugin_loaded('repeating'):
            plugins.unload('repeating')


class TestActions(ActionsBase):
    def test_prepare_zip_resources(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/posts')
        resource1 = factories.Resource(package_id=dataset['id'], url='https://jsonplaceholder.typicode.com/comments')
        resource_ids = [resource.get('id'), resource1.get('id')]
        data_dict = {'resources': resource_ids}
        result = actions.prepare_zip_resources({}, data_dict)
        assert 'zip_id' in result

    def test_add_spatial_data(self):
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
        result = spatial_data({'user': sysadmin.get('name'), 'auth_user_obj': user}, data_dict)
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
            resource = factories.Resource(package_id=dataset['id'], upload=test_resource)
        assert cm.exception.error_summary == {u'Message': u'Resource already exists'}

    def test_resource_delete(self):
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

    def test_start_script_valid_script_name(self):
        sysadmin = factories.Sysadmin()
        context = {'user': sysadmin.get('name')}
        data_dict = {'name': 'report'}

        result = actions.start_script(context, data_dict)

        assert result == 'Script was successfully executed.'

    def test_start_script_invalid_script_name(self):
        sysadmin = factories.Sysadmin()
        context = {'user': sysadmin.get('name')}
        data_dict = {'name': 'test'}

        with assert_raises(toolkit.ValidationError) as cm:
            result = actions.start_script(context, data_dict)

        assert cm.exception.error_dict == {'name': u'No script was found for the provided name'}

    def test_user_create(self):
        user = factories.Sysadmin()
        context = {'model': model, 'session': model.Session, 'user': user.get('name')}
        data_dict = {
            'name': 'test',
            'email': 'test@test.com',
            'password': '123456789'
        }
        test_helpers.call_action('user_create', context=context, **data_dict)

    def test_user_update(self):
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

    def test_user_activity_list(self):
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

    def test_user_activity_list_html_no_activities(cls):
        # Pylons needs to be mocked so that when calling the action
        # user_activity_list_html doesn't throw "TypeError: No object
        # (name: session) has been registered for this thread"
        mock_pylons()

        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'model': model
        }
        data_dict = {
            'id': user['id']
        }

        result = actions.user_activity_list_html({}, data_dict)

        assert 'No activities are within this activity stream' in result

    def test_user_activity_list_html_with_activity(cls):
        # Pylons needs to be mocked so that when calling the action
        # user_activity_list_html doesn't throw "TypeError: No object
        # (name: session) has been registered for this thread"
        mock_pylons()

        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'model': model,
            'session': model.Session,
        }
        data_dict = {
            'authority_file_url': 'test.png',
            'id': user['id'],
            'fullname': 'NewName',
            'email': 'example@example.com'
        }

        actions.user_update(context, data_dict)

        result = actions.user_activity_list_html({}, data_dict)

        assert 'updated their profile' in result

    def test_dashboard_activity_list_html_no_activities(cls):
        # Pylons needs to be mocked so that when calling the action
        # user_activity_list_html doesn't throw "TypeError: No object
        # (name: session) has been registered for this thread"
        mock_pylons()

        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'model': model
        }
        data_dict = {
            'id': user['id']
        }

        # Make sure a user is logged in to access the dashboard
        pylons.c.user = user['name']


        result = actions.dashboard_activity_list_html({}, data_dict)

        assert 'No activities are within this activity stream' in result

    def test_dashboard_activity_list_html_with_activity(cls):
        # Pylons needs to be mocked so that when calling the action
        # user_activity_list_html doesn't throw "TypeError: No object
        # (name: session) has been registered for this thread"
        mock_pylons()

        user = factories.Sysadmin()
        context = {
            'user': user['name'],
            'model': model,
            'session': model.Session,
        }
        data_dict = {
            'authority_file_url': 'test.png',
            'id': user['id'],
            'fullname': 'NewName',
            'email': 'example@example.com'
        }

        actions.user_update(context, data_dict)

        # Make sure a user is logged in to access the dashboard
        pylons.c.user = user['name']

        result = actions.dashboard_activity_list_html({}, data_dict)

        assert 'updated their profile' in result

    def test_dashboard_activity_list(self):
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

    def test_package_search(self):
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
        set_lang('mk')
        result = test_helpers.call_action('package_search', **data_dict)
        assert result.get('results')[0]['title'] == u'наслов на македонски'

    def test_get_package_stats(self):
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

        resource = factories.Resource(package_id=dataset['id'], url='http://www.google.com', upload=test_resource)
        resource2 = factories.Resource(package_id=dataset['id'], url='http://www.yahoo.com')

        increment_downloads(resource['id'])
        increment_downloads(resource['id'])
        increment_downloads(resource2['id'])


        result = actions.get_package_stats(dataset['id'])

        assert result['file_size'] == 669
        assert result['total_downloads'] == 3

    def test_increment_downloads_for_resource(self):
        dataset = create_dataset()
        resource = factories.Resource(package_id=dataset.get('id'), url='http://www.google.com')
        result = actions.increment_downloads_for_resource({}, {'resource_id': resource['id']})
        assert result == 'success'

    def test_resource_show_mk(self):
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
        set_lang('mk')
        result = test_helpers.call_action('resource_show', id=resource.get('id'))
        assert result.get('name') == 'name mk'
        assert result.get('description') == 'description mk'

    def test_resource_show_sq(self):
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
        set_lang('sq')
        result = test_helpers.call_action('resource_show', id=resource.get('id'))
        assert result.get('name') == 'name sq'
        assert result.get('description') == 'description sq'

    def test_organization_show_mk(self):
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
        set_lang('mk')
        result = test_helpers.call_action('organization_show', id=org.get('id'))
        assert result.get('title') == 'title mk'
        assert result.get('display_name') == 'title mk'
        assert result.get('description') == 'description mk'

    def test_organization_show_sq(self):
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
        set_lang('sq')
        result = test_helpers.call_action('organization_show', id=org.get('id'))
        assert result.get('title') == 'title sq'
        assert result.get('display_name') == 'title sq'
        assert result.get('description') == 'description sq'

    def test_group_show_mk(self):
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
        set_lang('mk')
        result = test_helpers.call_action('group_show', id=group.get('id'))
        assert result.get('title') == 'title mk'
        assert result.get('display_name') == 'title mk'
        assert result.get('description') == 'description mk'

    def test_group_show_sq(self):
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
        set_lang('sq')
        result = test_helpers.call_action('group_show', id=org.get('id'))
        assert result.get('title') == 'title sq'
        assert result.get('display_name') == 'title sq'
        assert result.get('description') == 'description sq'

    def test_get_related_datasets(self):
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

    def test_update_package_stats(self):
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

        resource = factories.Resource(package_id=dataset['id'], url='http://www.google.com', upload=test_resource)

        increment_downloads(resource['id'])
        increment_downloads(resource['id'])

        actions.update_package_stats(dataset['id'])

        solr_base_url = config['solr_url']
        url = '{0}/select?q=*:*&fq=id:{1}&wt=json'.format(solr_base_url, dataset['id'])

        result = requests.get(url)
        response = result.json().get('response')

        assert response.get('numFound') == 1
        assert response.get('docs')[0].get('extras_total_downloads') == '000000000000000000000002'
        assert response.get('docs')[0].get('extras_file_size') == '000000000000000000000669'
