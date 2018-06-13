
PRESETS = {
    "_generic_field":{
        "form_macro": "input",
        "classes": ["control-full", "control-large"],
    },
    "title": {
        "validators": "if_empty_same_as(name) unicode",
        "form-attrs": {
            "data-module": "slug-preview-target",
            "class": "form-control"
        },
        "classes": ["control-full", "control-large"],
        "form_macro": "input"
    },
    "dataset_slug": {
        "validators": "not_empty unicode name_validator package_name_validator",
        "form_snippet": "slug.html"
    },
    "multiple_checkbox": {
        "form_snippet": "multiple_checkbox.html",
        "display_snippet": "multiple_choice.html",
        "validators": "datagovmk_multiple_choice",
        "output_validators": "datagovmk_multiple_choice_output"
    },
    "dataset_organization": {
        "validators": "owner_org_validator unicode",
        "classes": ["control-full", "control-large"],
        "form_snippet": "organization.html"
    },
    "tag_string_autocomplete": {
        "validators": "ignore_missing tag_string_convert",
        "classes": ["control-full", "control-large"],
        "form-attrs": {
          "data-module": "autocomplete",
          "data-module-tags": "",
          "data-module-source": "/api/2/util/tag/autocomplete?incomplete=?"
        }
    },
    "select":{
        "form_snippet": "select.html",
        "display_snippet": "select.html",
        "validators": "datagovmk_required datagovmk_choices"
    },
    "date": {
        "form_snippet": "date.html",
        "display_snippet": "date.html",
        "validators": "datagovmk_required isodate convert_to_json_if_date",
        "classes": ["control-full", "control-large"],
    },
    "resource_url_upload": {
        "validators": "ignore_missing unicode remove_whitespace",
        "form_snippet": "upload.html",
        "form_placeholder": "http://example.com/my-data.csv",
        "upload_field": "upload",
        "upload_clear": "clear_upload",
        "upload_label": "File"
    },
    "resource_format_autocomplete": {
        "validators": "if_empty_guess_format ignore_missing clean_format unicode",
        "form_placeholder": "eg. CSV, XML or JSON",
        "form-attrs": {
          "data-module": "autocomplete",
          "data-module-source": "/api/2/util/resource/format_autocomplete?incomplete=?"
        }
    }
}