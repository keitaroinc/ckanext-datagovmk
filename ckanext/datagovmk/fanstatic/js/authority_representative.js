$(document).ready(function () {
    var authorityToggle = $('#authority_representative');
    var uploadAuthority = $('.upload-authority')

    $.each(authorityToggle, function (i, el) {
        if (el.checked) {
            uploadAuthority.removeClass('off')
        }
    });

    authorityToggle.click(function (e) {
        $.each(authorityToggle, function (i, el) {
            if (el.checked) {
                uploadAuthority.removeClass('off')
            } else {
                uploadAuthority.addClass('off')
            }
        });
    });
})
