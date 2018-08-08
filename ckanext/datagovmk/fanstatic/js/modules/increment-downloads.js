ckan.module('datagovmk-increment-downloads', function($) {
    console.log('test')
    return {
        initialize: function() {
            this.el.on('click', function(e) {
                var data = {
                    'resource_id': this.options.resource_id
                }
                $.get(window.location.origin + '/api/action/datagovmk_increment_downloads_for_resource', data)
            }.bind(this))
        }
    }
})
