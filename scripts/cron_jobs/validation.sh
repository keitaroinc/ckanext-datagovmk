CONFIG_FILE_LOCATION=$1

# Every 15 minutes
paster --plugin=ckanext-validation validation run --yes -c $CONFIG_FILE_LOCATION