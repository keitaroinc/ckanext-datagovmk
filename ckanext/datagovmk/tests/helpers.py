import uuid
from ckanext.datagovmk.model.user_authority import UserAuthority
from ckan.tests import factories
from ckan.plugins import toolkit


class User(object):
    def __init__(self, id):
        self.id = id


def create_dataset(**kwargs):
    sysadmin = factories.Sysadmin()

    data = {
        'user_id': sysadmin.get('id'),
        'authority_file': 'test.png',
        'authority_type': 'general'
    }

    userAuthority = UserAuthority(**data)
    userAuthority.save()

    user = User(sysadmin.get('id'))

    context = {'auth_user_obj': user, 'user': sysadmin.get('name')}

    data_dict = {
        'name': str(uuid.uuid4()),
        'add_dataset_agreement': 'yes',
        'title_translated-mk': 'title',
        'notes_translated-mk': 'notes',
        'maintainer': 'John',
        '_version_': 'v1.0.0'
    }
    data_dict.update(kwargs)
    return toolkit.get_action('package_create')(context, data_dict)


def set_lang(lang):
    from ckan.lib import i18n
    def get_lang_patched():
        return lang
    i18n.get_lang = get_lang_patched


def mock_pylons():
    from paste.registry import Registry
    import pylons
    from pylons.util import AttribSafeContextObj
    import ckan.lib.app_globals as app_globals
    from ckan.lib.cli import MockTranslator
    from ckan.config.routing import make_map
    from pylons.controllers.util import Request, Response
    from routes.util import URLGenerator

    class TestPylonsSession(dict):
        last_accessed = None

        def save(self):
            pass

    registry=Registry()
    registry.prepare()

    context_obj=AttribSafeContextObj()
    registry.register(pylons.c, context_obj)

    app_globals_obj = app_globals.app_globals
    registry.register(pylons.g, app_globals_obj)

    request_obj=Request(dict(HTTP_HOST="nohost", REQUEST_METHOD="GET"))
    registry.register(pylons.request, request_obj)

    translator_obj=MockTranslator()
    registry.register(pylons.translator, translator_obj)

    registry.register(pylons.response, Response())
    mapper = make_map()
    registry.register(pylons.url, URLGenerator(mapper, {}))
    registry.register(pylons.session, TestPylonsSession())
