CONFIG_FILE_LOCATION=$1

# Every hour
paster --plugin=ckanext-googleanalytics loadanalytics /var/lib/ckan/default/storage/ga_credentials.json -c $CONFIG_FILE_LOCATION
