# -*- coding: utf-8 -*-

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckanext.datagovmk.helpers as helpers
import json
from ckan.lib.plugins import DefaultTranslation
from ckan.logic import get_action
from routes.mapper import SubMapper
from ckanext.datagovmk import actions
from ckanext.datagovmk import auth
from ckanext.datagovmk.logic import import_spatial_data
from ckanext.datagovmk.utils import populate_location_name_from_spatial_uri
from ckanext.datagovmk import monkey_patch
from ckan.lib import email_notifications
from ckan.lib import base
from ckan.common import config


monkey_patch.activity_streams()
monkey_patch.validators()


def _notifications_for_activities(activities, user_dict):
    '''Return one or more email notifications covering the given activities.

    This function handles grouping multiple activities into a single digest
    email.

    :param activities: the activities to consider
    :type activities: list of activity dicts like those returned by
        ckan.logic.action.get.dashboard_activity_list()

    :returns: a list of email notifications
    :rtype: list of dicts each with keys 'subject' and 'body'

    '''
    if not activities:
        return []

    if not user_dict.get('activity_streams_email_notifications'):
        return []

    # We just group all activities into a single "new activity" email that
    # doesn't say anything about _what_ new activities they are.
    # TODO: Here we could generate some smarter content for the emails e.g.
    # say something about the contents of the activities, or single out
    # certain types of activity to be sent in their own individual emails,
    # etc.

    if len(activities) > 1:
        subject = u"{n} нови активности од {site_title} /{n} aktivitete të reja nga {site_title}/{n} new activities from {site_title}".format(
                site_title=config.get('ckan.site_title'),
                n=len(activities))
    else:
        subject = u"{n} нова активност од {site_title} / {n} aktivitet i ri nga {site_title} / {n} new activity from {site_title}".format(
                site_title=config.get('ckan.site_title'),
                n=len(activities))
    body = base.render(
            'activity_streams/activity_stream_email_notifications.text',
            extra_vars={'activities': activities})

    notifications = [{
        'subject': subject,
        'body': body
    }]

    return notifications

email_notifications._notifications_for_activities = _notifications_for_activities


class DatagovmkPlugin(plugins.SingletonPlugin, DefaultTranslation):
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.IPackageController, inherit=True)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'datagovmk')

        config_['licenses_group_url'] = '{0}/licenses.json'.format(config_['ckan.site_url'].rstrip('/'))

    # ITemplateHelpers
    def get_helpers(self):
        return {
            'datagovmk_get_recently_updated_datasets':
                helpers.get_recently_updated_datasets,
            'datagovmk_get_most_active_organizations':
                helpers.get_most_active_organizations,
            'datagovmk_get_groups':
                helpers.get_groups,
            'datagovmk_get_dataset_stats':
                helpers.get_dataset_stats,
            'datagovmk_get_resource_stats':
                helpers.get_resource_stats,
            'datagovmk_total_downloads':
                helpers.get_total_package_downloads,
            'datagovmk_get_related_datasets':
                helpers.get_related_datasets,
            'datagovmk_get_user_id':
                helpers.get_user_id,
            'datagovmk_get_last_authority_for_user':
                helpers.get_last_authority_for_user,
            'datagovmk_get_org_title':
                helpers.get_org_title,
            'datagovmk_get_org_description':
                helpers.get_org_description,
            'datagovmk_get_org_catalog':
                helpers.get_org_catalog,
            'datagovmk_get_catalog_count':
                helpers.get_catalog_count,
            'datagovmk_get_org_title_desc':
                helpers.get_org_title_desc,
            'datagovmk_get_translated':
                helpers.get_translated,
            'datagovmk_get_site_statistics':
                helpers.get_site_statistics,
            'get_config_option_show':
                helpers.get_config_option_show
        }

    # IActions

    def get_actions(self):
        package_create = get_action('package_create')
        package_update = get_action('package_update')
        #resource_delete = get_action('resource_delete')
        return {
            'datagovmk_get_related_datasets': actions.get_related_datasets,
            'datagovmk_prepare_zip_resources': actions.prepare_zip_resources,
            'datagovmk_increment_downloads_for_resource': actions.increment_downloads_for_resource,
            'package_create': actions.add_spatial_data(package_create),
            'package_update': actions.add_spatial_data(package_update),
            'resource_create': actions.resource_create,
            'resource_update': actions.resource_update,
            'datagovmk_start_script': actions.start_script,
            'user_create': actions.user_create,
            'user_update': actions.user_update,
            'user_activity_list': actions.user_activity_list,
            'user_activity_list_html': actions.user_activity_list_html,
            'dashboard_activity_list': actions.dashboard_activity_list,
            'dashboard_activity_list_html': actions.dashboard_activity_list_html,
            'package_search': actions.package_search,
            'resource_show': actions.resource_show,
            'organization_show': actions.organization_show,
            'group_show': actions.group_show,
            'resource_delete': actions.resource_delete
        }

    # IAuthFunctions

    def get_auth_functions(self):
        return {
            'datagovmk_get_related_datasets': auth.get_related_datasets,
            'datagovmk_get_groups': helpers.get_groups,
            'datagovmk_start_script': auth.start_script,
        }

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')
        validators = [ignore_missing, unicode]

        schema.update({
            'footer_links': validators,
            'ckan.site_about_en': validators,
            'ckan.site_about_mk': validators,
            'ckan.site_about_sq': validators,
            'ckan.site_intro_text_en': validators,
            'ckan.site_intro_text_mk': validators,
            'ckan.site_intro_text_sq': validators
        })

        return schema

    # IRoutes
    def before_map(self, map):
        map.connect(
            '/api/i18n/{lang}',
            controller='ckanext.datagovmk.controller:ApiController',
            action='i18n_js_translations'
        )
        map.connect('/api/download/{package_id}/resources',
                    controller='ckanext.datagovmk.controller:BulkDownloadController',
                    action='download_resources_metadata')
        map.connect('/api/download/{package_id}/metadata',
                    controller='ckanext.datagovmk.controller:BulkDownloadController',
                    action='download_package_metadata')

        # Override the resource download links, so we can count the number of downloads.
        with SubMapper(map, controller='ckanext.datagovmk.controller:DownloadController') as m:
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download',
                      action='resource_download')
            m.connect('resource_download',
                      '/dataset/{id}/resource/{resource_id}/download/{filename}',
                      action='resource_download')
            m.connect('download_zip',
                      '/download/zip/{zip_id}',
                      action='download_zip')
            m.connect('search',
                      '/dataset',
                      action='search')

        # map user routes
        with SubMapper(map, controller='ckanext.datagovmk.controller:DatagovmkUserController') as m:
            m.connect('register', '/user/register', action='datagovmk_register')
            m.connect('/user/activate/{id:.*}', action='perform_activation')

        map.connect('/issues/report_site_issue',
                    controller='ckanext.datagovmk.controller:ReportIssueController',
                    action='report_issue_form')

        map.connect('/datastore/dump/{resource_id}',
                    controller='ckanext.datagovmk.controller:OverrideDatastoreController',
                    action='dump')

        map.connect('/stats',
                    controller="ckanext.datagovmk.controller:StatsController",
                    action="index")

        return map

    # IPackageController
    def before_index(self, pkg_dict):
        if 'title_translated' in pkg_dict:
            titles = pkg_dict['title_translated']
            titles_json = json.loads(titles)
            pkg_dict['title_en'] = titles_json["en"].lower()
            pkg_dict['title_mk'] = titles_json["mk"].lower()
            pkg_dict['title_sq'] = titles_json["sq"].lower()
        stats = actions.get_package_stats(pkg_dict['id'])
        if stats:
            pkg_dict['extras_file_size'] = str(stats.get('file_size') or '0').rjust(24, '0')
            pkg_dict['extras_total_downloads'] = str(stats.get('total_downloads') or '0').rjust(24, '0')

        populate_location_name_from_spatial_uri(pkg_dict)
        return pkg_dict

    def before_view(self, pkg_dict):
        return pkg_dict


    def before_search(self, search_params):
        """ Before making a search with package_search, make sure to exclude
        datasets that are marked as catalogs. """
        fq = search_params.get('fq', '')
        q = search_params.get('q', '')

        if 'extras_org_catalog_enabled' not in fq and \
           'extras_org_catalog_enabled:true' not in q:
            search_params.update({'fq': fq + ' -extras_org_catalog_enabled:true'})

        return search_params
