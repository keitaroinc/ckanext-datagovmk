from flask import Blueprint
from logging import getLogger
from datetime import datetime


import ckan.model as model
import ckan.lib.helpers as h
from ckan.views.admin import _get_sysadmins
from ckan.plugins.toolkit import _, c, request, config, render

from ckanext.datagovmk.utils import send_email

log = getLogger(__name__)

report_issue = Blueprint('report_issue', __name__)

def report_issue_form():
    """Renders the issue reporting form and reports the issue by sending
    an email to the system admin with the issue.
    """
    login_required = False
    if not c.user:
        login_required = True

    data_dict = {}
    errors = {
        'issue_title': [],
        'issue_description': []
    }
    extra_vars = {
        'data': data_dict,
        'errors': errors,
        'login_required': login_required
    }
    if request.method == 'POST':
        data_dict['issue_title'] = request.form.get('issue_title')
        data_dict['issue_description'] = request.form.get('issue_description')

    if login_required:
        return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)


    if request.method != 'POST':
        return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)



    context = {'model': model, 'session': model.Session,
                'user': c.user, 'auth_user_obj': c.userobj}

    to_user = get_admin_email()

    if not to_user:
        h.flash_error(_('Unable to send the issue report to the system admin.'))
        return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)

    issue_title = data_dict['issue_title'].strip()

    issue_description = h.render_markdown(data_dict['issue_description'])

    email_content = render('datagovmk/issue_email_template.html', extra_vars={
        'title': issue_title,
        'site_title': config.get('ckan.site_title', 'CKAN'),
        'description': issue_description,
        'date': datetime.now(),
        'username': c.userobj.fullname or c.userobj.name,
        'user': c.userobj,
        'user_url': h.url_for('user.read', id=c.user, qualified=True)
    })

    subject = u'CKAN: Проблем | Problem | Issue: {title}'.format(title=issue_title)

    result = send_email(to_user['name'], to_user['email'], subject, email_content)

    if not result['success']:
        h.flash_error(result['message'])
    else:
        h.flash_success(toolkit._('The issue has been reported.'))
        extra_vars['successfuly_reported'] = True
    return render('datagovmk/report_issue_form.html', extra_vars=extra_vars)


def get_admin_email():
    """Loads the admin email.

    If a system configuration is present, it is preffered to the CKAN sysadmins.
    The configuration property is ``ckanext.datagovmk.site_admin_email``.

    If no email is configured explicitly, then the email of the first CKAN
    sysadmin is used.

    :returns: ``str`` the email of the sysadmin to which to send emails with
        issues.

    """
    sysadmin_email = config.get('ckanext.datagovmk.site_admin_email', False)
    if sysadmin_email:
        name = sysadmin_email.split('@')[0]
        return {
            'email': sysadmin_email,
            'name': name
        }
    sysadmins = _get_sysadmins()
    if sysadmins:
        return {
            'email': sysadmins[0].email,
            'name': sysadmins[0].fullname or sysadmins[0].name
        }
    return None


report_issue.add_url_rule('/issues/report_site_issue',
                          view_func=report_issue_form,
                          methods=['GET', 'POST'])