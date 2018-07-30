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

    data_dict = {'name': str(uuid.uuid4()), 'add_dataset_agreement': 'yes'}
    data_dict.update(kwargs)
    return toolkit.get_action('package_create')(context, data_dict)