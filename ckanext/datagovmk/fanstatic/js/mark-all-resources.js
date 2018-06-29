$(document).ready(function () {

    // When the Mark All button is clicked, toggle the state for checkboxes
    // displayed next to each resource
    $('.btn-mark-all').click(function (e) {
        var $el = $(this);
        var checkboxInput = $el.parent().parent().parent().find('input[type=checkbox]');
        if (!$el.data('status')) {
            checkboxInput.prop('checked', true).change();
            $el.data('status', 'marked').html("Unmark All");
        } else {
            checkboxInput.prop('checked', false).change();
            $el.data('status', null).html("<span class='fa fa-check'></span> Mark All");
        }
    });

});
