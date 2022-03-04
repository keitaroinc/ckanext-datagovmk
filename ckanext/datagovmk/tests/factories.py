import factory

import ckan.model
import ckan.logic
import ckan.tests.helpers as helpers
from ckan import model
from ckan.logic.action.create import user_create as _user_create


def _generate_email(user):
    """Return an email address for the given User factory stub object."""

    return "{0}@ckan.org".format(user.name).lower()


class User(factory.Factory):
    """A factory class for creating CKAN users."""

    # This is the class that UserFactory will create and return instances
    # of.
    class Meta:
        model = ckan.model.User

    # These are the default params that will be used to create new users.
    fullname = "Mr. Test User"
    password = "RandomPassword123"
    about = "Just another test user."
    image_url = "https://placekitten.com/g/200/100"

    # Generate a different user name param for each user that gets created.
    name = factory.Sequence(lambda n: "test_user_{0:02d}".format(n))

    # Compute the email param for each user based on the values of the other
    # params above.
    email = factory.LazyAttribute(_generate_email)

    # I'm not sure how to support factory_boy's .build() feature in CKAN,
    # so I've disabled it here.
    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    # To make factory_boy work with CKAN we override _create() and make it call
    # a CKAN action function.
    # We might also be able to do this by using factory_boy's direct SQLAlchemy
    # support: http://factoryboy.readthedocs.org/en/latest/orms.html#sqlalchemy
    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        if args:
            assert False, "Positional args aren't supported, use keyword args."
        context = {'model': ckan.model,
                   'session': ckan.model.Session, 'user': ''}
        data_dict = {**kwargs}
        user_dict = _user_create(context, data_dict)
        return user_dict


class Dataset(factory.Factory):
    """A factory class for creating CKAN datasets."""

    class Meta:
        model = ckan.model.Package

    # These are the default params that will be used to create new groups.
    title = "Test Dataset"
    title_translated =  {"mk": u"Тест Податоченсет"}
    notes = "Just another test dataset."
    notes_translated = {"mk": "Уште еден тест"}
    maintainer = "Someone"

    # Generate a different group name param for each user that gets created.
    name = factory.Sequence(lambda n: "test_dataset_{0:02d}".format(n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise NotImplementedError(".build() isn't supported in CKAN")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        data = {**kwargs}
        print(data)
        if args:
            assert False, "Positional args aren't supported, use keyword args."

        user = data['user']
        user_obj = model.User.get(user['id'])

        context = {'auth_user_obj': user_obj}

        dataset_dict = helpers.call_action(
            "package_create", context=context, **kwargs
        )
        return dataset_dict
