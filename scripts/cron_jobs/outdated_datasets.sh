CONFIG_FILE_LOCATION=$1

# Every day
paster --plugin=ckanext-datagovmk check_outdated_datasets -c $CONFIG_FILE_LOCATION