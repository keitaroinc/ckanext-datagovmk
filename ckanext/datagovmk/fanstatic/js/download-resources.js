$(document).ready(function () {

  var _ = ckan.i18n.ngettext;
  var downloadResourcesBtn = $('#download-resources');
  var resourceCheckboxes = $('input[name=mark-download-resource]');

  // When the Mark All button is clicked, toggle the state for checkboxes displayed next to each resource
  $('.btn-mark-all').click(function (e) {
    var $el = $(this);
    if (!$el.data('status')) {
      downloadResourcesBtn.addClass('btn-success');
      downloadResourcesBtn.removeAttr('disabled');
    } else {
      downloadResourcesBtn.removeClass('btn-success');
      downloadResourcesBtn.attr('disabled', 'disabled');
    }
  });

  // Disable/enable the Download button depending if any checkbox is checked.
  resourceCheckboxes.click(function (e) {
    var atLeastOneChecked = false;

    $.each(resourceCheckboxes, function (i, el) {
      if (el.checked) {
        atLeastOneChecked = true;
      }
    });

    if (atLeastOneChecked) {
      downloadResourcesBtn.addClass('btn-success');
      downloadResourcesBtn.removeAttr('disabled');
    } else {
      downloadResourcesBtn.removeClass('btn-success');
      downloadResourcesBtn.attr('disabled', 'disabled');
    }
  });

  downloadResourcesBtn.click(function (e) {
    var url = window.location.origin + '/api/action/datagovmk_prepare_zip_resources';
    var data = { resources: [] };

    downloadResourcesBtn.attr('disabled', 'disabled');
    downloadResourcesBtn.text(_('Preparing zip archive...'));

    $.each(resourceCheckboxes, function (i, el) {
      if (el.checked) {
        data.resources.push(el.value);
      }
    });

    $.post(url, JSON.stringify(data), function (response) {
      var zip_id = response.result.zip_id;

      downloadResourcesBtn.removeAttr('disabled');
      downloadResourcesBtn.text(_('Download'));

      if (zip_id) {
        var link = document.createElement('a');
        url = window.location.origin + '/api/action/datagovmk_download_zip?id=' + zip_id;
        link.style.display = 'none';
        link.href = url;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        window.ckan.notify(_('Could not create a zip archive.'));
      }
    }).error(function (response) {
      downloadResourcesBtn.removeAttr('disabled');
      downloadResourcesBtn.text(_('Download'));

      window.ckan.notify(_('An error occured while preparing zip archive.'));
    });
  });

});
