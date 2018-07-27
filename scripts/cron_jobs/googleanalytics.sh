CONFIG_FILE_LOCATION=$1

# Every hour
paster --plugin=ckanext-googleanalytics loadanalytics credentials.json -c $CONFIG_FILE_LOCATION
