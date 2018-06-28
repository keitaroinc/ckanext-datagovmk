from ckan.plugins import toolkit

_ = toolkit._
ValidationError = toolkit.ValidationError
get_action = toolkit.get_action


@toolkit.side_effect_free
def get_related_datasets(context, data_dict):

    '''This is an action function which returns related datasets for a single dataset, based
    on groups and tags which are parts of the dataset itself.
    
    :param id: id od the single dataset for which we would like to return
        the related datasets
    :type id: string
    
    :param limit: Limit of the datasets to be returned, default is 3
    :type limit: integer

    :returns: a list of datasets which are related with the one we have chosen
    :rtype: list
    
    '''

    id = data_dict.get('id')
    limit = int(data_dict.get('limit', 3))
    related_datasets = []
    related_datasets_ids = []

    if id is None:
        raise ValidationError(_('Missing dataset id'))

    dataset = get_action('package_show')(data_dict={'id': id})

    groups = dataset.get('groups')
    tags = dataset.get('tags')

    for group in groups:
        data_dict = {
            'id': group.get('id'),
            'include_datasets': True
        }
        group_dict = get_action('group_show')(data_dict=data_dict)

        group_datasets = group_dict.get('packages')

        for group_dataset in group_datasets:
            group_dataset_id = group_dataset.get('id')
            if group_dataset_id != dataset.get('id') and \
               group_dataset_id not in related_datasets_ids:
                related_datasets.append(group_dataset)
                related_datasets_ids.append(group_dataset_id)

    for tag in tags:
        data_dict = {
            'id': tag.get('id'),
            'include_datasets': True
        }
        tag_dict = get_action('tag_show')(data_dict=data_dict)

        tag_datasets = tag_dict.get('packages')

        for tag_dataset in tag_datasets:
            tag_dataset_id = tag_dataset.get('id')
            if tag_dataset_id != dataset.get('id') and \
               tag_dataset_id not in related_datasets_ids:
                related_datasets.append(tag_dataset)
                related_datasets_ids.append(tag_dataset_id)

    return related_datasets[:limit]
