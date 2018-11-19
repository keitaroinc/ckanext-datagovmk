CONFIG_FILE_LOCATION=$1

# Every hour
paster --plugin=ckanext-datagovmk fetch_most_active_orgs -c $CONFIG_FILE_LOCATION
