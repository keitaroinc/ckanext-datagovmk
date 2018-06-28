"""Controllers definitions and overrides.
"""
from ckan.controllers.package import PackageController
from ckanext.datagovmk.model.stats import increment_downloads
from ckan.lib.base import BaseController
import os
from ckan.plugins import toolkit

class DownloadController(PackageController):
    """Overrides CKAN's PackageController to add count for the resource downloads.
    """

    def resource_download(self, id, resource_id, filename=None):
        """Overrides CKAN's ``resource_download`` action and adds counting of the
        number of downloads per resource.

        :param id: dataset id
        :type id: string

        :param resource_id: resource id
        :type resource_id: string

        """
        increment_downloads(resource_id)
        return super(DownloadController, self).resource_download(id, resource_id, filename)


class ApiController(BaseController):
    def i18n_js_translations(self, lang):
        ''' Patch for broken JS translations caused by Pylons to Flask
        migration. This method patches https://github.com/ckan/ckan/blob/master/ckan/views/api.py#L467 
        
        :param lang: locale of the language
        :type lang: string

        :returns: the translated strings in a json file.
        
        :rtype: json
        
        '''

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
