$(document).ready(function () {
    var authorityToggle = $('#authority_representative');
    var uploadAuthority = $('.upload-authority')

    $.each(authorityToggle, function (i, el) {
        if (el.checked) {
            uploadAuthority.removeClass('invisible')
        }
    });

    authorityToggle.click(function (e) {
        $.each(authorityToggle, function (i, el) {
            if (el.checked) {
                uploadAuthority.removeClass('invisible')
            } else {
                uploadAuthority.addClass('invisible')
            }
        });
    });
})
