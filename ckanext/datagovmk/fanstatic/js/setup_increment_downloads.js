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
