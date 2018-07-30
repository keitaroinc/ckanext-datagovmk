CONFIG_FILE_LOCATION=$1

# Every night on midnight
paster --plugin=ckanext-report report generate -c $CONFIG_FILE_LOCATION
