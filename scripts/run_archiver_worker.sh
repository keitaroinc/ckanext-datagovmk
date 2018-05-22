# Runs the CKAN background job worker, specificaly for the queue 'bulk' for the archiver extension.
paster --plugin=ckan jobs worker bulk --config="${APP_DIR}/production.ini"
