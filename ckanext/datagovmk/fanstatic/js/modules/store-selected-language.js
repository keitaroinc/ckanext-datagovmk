ckan.module('datagovmk-store-selected-language', function($) {
    return {
        initialize: function() {
            this.el.on('click', function() {
                window.localStorage.setItem('selected_locale', this.options.locale)
            }.bind(this))
        }
    }
})
