# These jobs should be run periodically (cronjobs).

# Fetch GA stats - this job should be run more often - once an hour or so
# because this fetches the actual number of visits per package/resource.
# * Run it from ckanext-googleanalytics directory
# * You MUST have the credentials.json from GA

paster loadanalytics credentials.json -c /etc/ckan/default/development.ini

# Fetch all events - this can be run less often - once or twice a month.
# This fetches all tracking info from GA and stores it in CKAN.
# * Run it from ckanext-googleanalytics directory
# * You MUST have the credentials.json from GA

paster loadanalytics credentials.json internal 2018-06-01 -c /etc/ckan/default/development.ini
