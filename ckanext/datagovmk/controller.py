"""Controllers definitions and overrides.
"""
from ckan.controllers.package import PackageController
from ckanext.datagovmk.model.stats import increment_downloads

class DownloadController(PackageController):
    """Overrides CKAN's PackageController to add count for the resource downloads.
    """

    def resource_download(self, id, resource_id, filename=None):
        """Overrides CKAN's ``resource_download`` action and adds counting of the
        number of downloads per resource.
        """
        increment_downloads(resource_id)
        return super(DownloadController, self).resource_download(id, resource_id, filename)