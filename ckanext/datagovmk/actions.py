from ckan.plugins import toolkit

_ = toolkit._
ValidationError = toolkit.ValidationError
get_action = toolkit.get_action


@toolkit.side_effect_free
def get_related_datasets(context, data_dict):
    id = data_dict.get('id')
    limit = data_dict.get('limit', 3)
    related_datasets = []

    if id is None:
        raise ValidationError(_('Missing dataset id'))

    dataset = get_action('package_show')(data_dict={'id': id})

    groups = dataset.get('groups')
    tags = dataset.get('tags')

    if len(groups) > 0:
        for group in groups:
            data_dict = {
                'id': group.get('id'),
                'include_datasets': True
            }
            group_dict = get_action('group_show')(data_dict=data_dict)

            if group_dict.get('package_count') > 1:
                group_datasets = group_dict.get('packages')

                for group_dataset in group_datasets:
                    if group_dataset.get('id') != dataset.get('id'):
                        related_datasets.append(group_dataset)

    if len(tags) > 0:
        for tag in tags:
            pass

    return related_datasets[:limit]
