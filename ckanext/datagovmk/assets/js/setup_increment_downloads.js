/*
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
*/

$(document).ready(function() {
    // Attach JS module for incrementing downloads for a resource
    //  "Download" and "Download as" buttons
    var downloadButton = $('a.btn-primary.resource-url-analytics')
    var resourceId = $('div[data-resource-id]').attr('data-resource-id')

    if (downloadButton.length == 1) {
        downloadButton.attr('data-module', 'datagovmk-increment-downloads')
        downloadButton.attr('data-module-resource_id', resourceId)
    }

    var otherDownloadFormatsContainer = downloadButton.parent().find('ul.dropdown-menu')

    $.each(otherDownloadFormatsContainer.find('a'), function() {
        $(this).attr('data-module', 'datagovmk-increment-downloads')
        $(this).attr('data-module-resource_id', resourceId)
    })
})
