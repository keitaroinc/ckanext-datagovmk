CONFIG_FILE_LOCATION=$1

# Weekly at 3am
paster --plugin=ckanext-archiver archiver update -c $CONFIG_FILE_LOCATION
