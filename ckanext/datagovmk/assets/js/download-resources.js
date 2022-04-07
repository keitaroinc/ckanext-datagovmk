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
  var downloadResourcesBtn = $('#download-resources');
  var resourceCheckboxes = $('input[name=mark-download-resource]');
  var downloadMetadata = $('a.download-metadata');


  var clickLinkInBackground = function(url) {
    var link = document.createElement('a');
    link.style.display = 'none';
    link.href = url;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  var toggleDownloadButtons = function(){
    var atLeastOneChecked = false;

    $.each(resourceCheckboxes, function (i, el) {
      if (el.checked) {
        atLeastOneChecked = true;
      }
    });

    if (atLeastOneChecked) {
      $.each([downloadResourcesBtn, $('.download-metadata-btn'), $('.download-metadata-control .btn')], function(i, elem){
        elem.addClass('btn-success');
        elem.removeAttr('disabled');
      });
    } else {
      $.each([downloadResourcesBtn, $('.download-metadata-btn'), $('.download-metadata-control .btn')], function(i, elem){
        elem.removeClass('btn-success');
        elem.attr('disabled', 'disabled');
      });
    }
  };

  // When the Mark All button is clicked, toggle the state for checkboxes displayed next to each resource
  $('.btn-mark-all').click(function (e) {
    // reschedule it at the end of the event queue, give it time to enable the checkboxes.
    setTimeout(function(){
      toggleDownloadButtons();
    }, 0);
  });

  // Disable/enable the Download button depending if any checkbox is checked.
  resourceCheckboxes.click(function (e) {
    toggleDownloadButtons();
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
        url = window.location.origin + '/download/zip/' + zip_id;
        link.style.display = 'none';
        link.href = url;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } else {
        window.ckan.notify(_('Could not create a zip archive.'));
      }
    }).fail(function (response) {
      downloadResourcesBtn.removeAttr('disabled');
      downloadResourcesBtn.text(_('Download'));

      window.ckan.notify(_('An error occured while preparing zip archive.'));
    });
  });

  downloadMetadata.click(function(e){
    e.preventDefault();
    e.stopPropagation();
    var resources = []
    if ( $(this).attr('disabled') ) {
      return;
    }
    $.each(resourceCheckboxes, function (i, el) {
      if (el.checked) {
        resources.push(el.value);
      }
    });
    var url = $(this).attr('href')
    if (resources.length){
      url += '&resources=' + resources.join(',')
    }
    clickLinkInBackground(url)
  });


  toggleDownloadButtons(); // first time we load.

});
