"""Controllers definitions and overrides.
"""
import os
import paste.fileapp
import mimetypes

from ckan.controllers.package import PackageController
from ckanext.datagovmk.model.stats import increment_downloads
from ckan.lib.base import BaseController, abort
from ckan.plugins import toolkit
from ckan.common import c, request, response

import ckan.model as model
import ckan.logic as logic
import ckan.lib.uploader as uploader
import ckan.lib.helpers as h

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
get_action = logic.get_action


class DownloadController(PackageController):
    """Overrides CKAN's PackageController to add count for the resource downloads.
    """

    def resource_download(self, id, resource_id, filename=None):
        """Overrides CKAN's ``resource_download`` action. Adds counting of the
        number of downloads per resource and provides a direct download by downloading
        an uploaded file directly
        """
        increment_downloads(resource_id)

        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}

        try:
            rsc = get_action('resource_show')(context, {'id': resource_id})
            get_action('package_show')(context, {'id': id})
        except (NotFound, NotAuthorized):
            abort(404, _('Resource not found'))

        if rsc.get('url_type') == 'upload':
            upload = uploader.get_resource_uploader(rsc)
            filepath = upload.get_path(rsc['id'])
            fileapp = paste.fileapp.FileApp(filepath)
            try:
                status, headers, app_iter = request.call_application(fileapp)
            except OSError:
                abort(404, _('Resource data not found'))
            response.headers.update(dict(headers))
            content_type, content_enc = mimetypes.guess_type(
                rsc.get('url', ''))
            if content_type:
                response.headers['Content-Type'] = content_type
            response.content_disposition = 'attachment; filename="%s"' % filename
            response.status = status
            return app_iter
        elif 'url' not in rsc:
            abort(404, _('No download is available'))
        h.redirect_to(rsc['url'])


class ApiController(BaseController):
    def i18n_js_translations(self, lang):
        ''' Patch for broken JS translations caused by Pylons to Flask
        migration. This method patches https://github.com/ckan/ckan/blob/master/ckan/views/api.py#L467 '''
        ckan_path = os.path.join(
            os.path.dirname(__file__), '..', '..', '..', 'ckan', 'ckan'
        )
        source = os.path.abspath(os.path.join(ckan_path, 'public',
                                 'base', 'i18n', '%s.js' % lang))
        toolkit.response.headers['Content-Type'] =\
            'application/json;charset=utf-8'
        if not os.path.exists(source):
            return '{}'
        f = open(source, 'r')
        return(f)
