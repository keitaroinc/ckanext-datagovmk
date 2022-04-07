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

$(document).ready(function () {

    var _ = ckan.i18n.ngettext;
    // When the Mark All button is clicked, toggle the state for checkboxes
    // displayed next to each resource
    $('.btn-mark-all').click(function (e) {
        var $el = $(this);
        var checkboxInput = $el.parent().parent().parent().find('input[type=checkbox]');
        if (!$el.data('status')) {
            checkboxInput.prop('checked', true).change();
            $el.data('status', 'marked').html("<span class='fa fa-minus-square'></span> " + _('Unmark All'));
        } else {
            checkboxInput.prop('checked', false).change();
            $el.data('status', null).html("<span class='fa fa-check-square'></span> " + _('Mark All'));
        }
    });

});
