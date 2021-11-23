from urllib.parse import urlencode
from urllib.request import urlopen
import json

from logging import getLogger
from flask import Blueprint

from ckan.plugins import toolkit
from ckan import authz
from ckan.plugins.toolkit import _, c, g, request, abort, config
from ckan.lib.navl import dictization_functions
from ckan.lib import captcha
import ckan.model as model
import ckan.logic as logic
import ckan.lib.helpers as h
from ckan.views.user import RegisterView, set_repoze_user
import ckan.lib.base as base

from ckanext.datagovmk.lib import (verify_activation_link,
                                   create_activation_key)


log = getLogger(__name__)

override_user = Blueprint('override_user', __name__)


def _check_recaptcha(remote_ip, recaptcha_response):
    '''Check a user\'s recaptcha submission is valid, and raise CaptchaError
    on failure.'''

    recaptcha_private_key = config.get('ckan.recaptcha.privatekey', '')
    if not recaptcha_private_key:
        # Recaptcha not enabled
        return

    recaptcha_server_name = 'https://www.google.com/recaptcha/api/siteverify'

    # recaptcha_response_field will be unicode if there are foreign chars in
    # the user input. So we need to encode it as utf8 before urlencoding or
    # we get an exception (#1431).
    params = urlencode(dict(secret=recaptcha_private_key,
                            emoteip=remote_ip,
                            response=recaptcha_response))
    f = urlopen(recaptcha_server_name, params)
    data = json.load(f)
    f.close()

    try:
        if not data['success']:
            return False
        else:
            return True
    except IndexError:
        # Something weird with recaptcha response
        return False


class OverrideRegisterView(RegisterView):

    def post(self):
        context = self._prepare()
        came_from = request.params.get('came_from')
        try:
            data_dict = logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.form))))
            data_dict.update(logic.clean_dict(
                dictization_functions.unflatten(
                    logic.tuplize_dict(logic.parse_params(request.files)))
            ))

            context['message'] = data_dict.get('log_message', '')

            # recaptcha_response = data_dict['g-recaptcha-response']
            remote_ip = request.environ.get('REMOTE_ADDR',
                                            'Unknown IP Address')

            # if ( _check_recaptcha(remote_ip, recaptcha_response) ):
            #     user = toolkit.get_action('user_create')(context, data_dict)
            # else:
            #     error_msg = _(u'Bad Captcha. Please try again.')
            #     h.flash_error(error_msg)
            #     return self.new(data_dict)
        except dictization_functions.DataError:
            base.abort(400, _(u'Integrity Error'))

        context[u'message'] = data_dict.get(u'log_message', u'')
        # try:
        #     captcha.check_recaptcha(request)
        # except captcha.CaptchaError:
        #     error_msg = _(u'Bad Captcha. Please try again.')
        #     h.flash_error(error_msg)
        #     return self.get(data_dict)

        try:
            logic.get_action(u'user_create')(context, data_dict)
        except logic.NotAuthorized:
            base.abort(403, _(u'Unauthorized to create user %s') % u'')
        except logic.NotFound:
            base.abort(404, _(u'User not found'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            return self.get(data_dict, errors, error_summary)

        h.flash_success(_('A confirmation email has been sent to %s. '
                          'Please use the link in the email to continue.') %
                        data_dict['email'])

        if not g.user:
            # Do not log in the user programatically
            # set_repoze_user(data_dict['name'])
            if came_from:
                h.redirect_to(came_from)
            else:
                # redirect user to login page
                # h.redirect_to(controller='user', action='me')
                h.redirect_to('user.login')
        else:
            # #1799 User has managed to register whilst logged in - warn user
            # they are not re-logged in as new user.
            h.flash_success(
                _(u'User "%s" is now registered but you are still '
                  u'logged in as "%s" from before') % (data_dict[u'name'],
                                                       g.user))
            if authz.is_sysadmin(g.user):
                # the sysadmin created a new user. We redirect him to the
                # activity page for the newly created user
                return h.redirect_to(u'user.activity', id=data_dict[u'name'])
            else:
                return base.render(u'user/logout_first.html')

        # log the user in programatically
        resp = h.redirect_to(u'user.me')
        set_repoze_user(data_dict[u'name'], resp)
        return resp

    def perform_activation(self, id):
        """ Activates user account

        :param id: user ID
        :type id: string

        """

        context = {'model': model, 'session': model.Session,
                   'user': id, 'keep_email': True}

        try:
            data_dict = {'id': id}
            user_dict = toolkit.get_action('user_show')(context, data_dict)

            user_obj = context['user_obj']
        except logic.NotFound:
            abort(404, _('User not found'))

        c.activation_key = request.args.get('key')
        if not verify_activation_link(user_obj, c.activation_key):
            h.flash_error(_('Invalid activation key. Please try again.'))
            abort(403)

        try:
            user_dict['reset_key'] = c.activation_key
            user_dict['state'] = model.State.ACTIVE
            toolkit.get_action('user_update')(context, user_dict)
            create_activation_key(user_obj)

            h.flash_success(_('Your account has been activated.'))

        except logic.NotAuthorized:
            h.flash_error(_('Unauthorized to edit user %s') % id)
        except logic.NotFound:
            h.flash_error(_('User not found'))
        except dictization_functions.DataError:
            h.flash_error(_(u'Integrity Error'))
        except logic.ValidationError as e:
            h.flash_error(u'%r' % e.error_dict)
        except ValueError as ve:
            h.flash_error(str(ve))

        c.user_dict = user_dict
        return h.redirect_to('user.login')


override = OverrideRegisterView()


override_user.add_url_rule('/user/register',
                           view_func=override.post,
                           methods=["POST"])
override_user.add_url_rule('/user/activate/<id>',
                           view_func=override.perform_activation,
                           methods=["GET"])
