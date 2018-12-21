CONFIG_FILE_LOCATION=$1

paster --plugin=ckan search-index rebuild -r -c $CONFIG_FILE_LOCATION
