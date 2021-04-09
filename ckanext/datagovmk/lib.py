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

from ckan.common import config
from ckan.lib.base import render_jinja2
from ckan.lib import helpers as h
from ckan.lib import mailer


def create_activation_key(user):
    """ Creates activation key for user
    :param user: the user for whom an activation key should be created
    :type user: dict
    """
    mailer.create_reset_key(user)


def get_activation_link(user):
    """ Get activation link for the user
    :param user: the user for whom an activation link should be gotten
    :type user: dict
    :returns: activation link
    :rtype: str
    """
    controller_path = 'ckanext.datagovmk.controller:DatagovmkUserController'
    return h.url_for(controller=controller_path,
                     action='perform_activation',
                     id=user.id,
                     key=user.reset_key,
                     qualified=True)


def request_activation(user):
    """ Request activation for user
    :param user: the user for whom an activation link should be requested
    :type user: dict
    """

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

    mailer.mail_recipient(user.name, user.email, subject, body, headers={})


def verify_activation_link(user, key):
    """ Verifies the activation link
    :param user: checks if the activation link is verified for the user
    :type user: object
    :param key: the activation key
    :type key: str
    """
    if not user or not key:
        return False
    if not user.reset_key or len(user.reset_key) < 5:
        return False
    return key.strip() == user.reset_key
