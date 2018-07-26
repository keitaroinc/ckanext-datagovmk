from ckan.common import config
from ckan.lib.base import render_jinja2
from ckan.lib import helpers as h
from ckan.lib import mailer


def create_activation_key(user):
    mailer.create_reset_key(user)


def get_activation_link(user):
    controller_path = 'ckanext.datagovmk.controller:DatagovmkUserController'
    return h.url_for(controller=controller_path,
                     action='perform_activation',
                     id=user.id,
                     key=user.reset_key,
                     qualified=True)


def request_activation(user):
    create_activation_key(user)
    site_title = config.get('ckan.site_title')
    site_url = config.get('ckan.site_url')

    body = render_jinja2('emails/confirm_user_email.txt', {
        'activation_link': get_activation_link(user),
        'site_url': site_url,
        'site_title': site_title,
        'user_name': user.name
    })
    subject = render_jinja2('emails/confirm_user_subject.txt', {
        'site_title': site_title
    })
    subject = subject.split('\n')[0]

    mailer.mail_user(user, subject, body)


def verify_activation_link(user, key):
    if not user or not key:
        return False
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key