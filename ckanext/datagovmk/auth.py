def get_related_datasets(context, data_dict):

    '''This is an authentication function which allows only
    registered users to access the action

    :py:func:`~ckanext.datagovmk.actions.get_related_datasets`

    '''

    return {'success': True}


def start_script(context, data_dict):
    """ This is a sensitive action, so only sysadmins are allowed to execute
    it """
    return {'success': False}
