# ckanext-report initdb
paster --plugin=ckanext-report report initdb --config="${APP_DIR}/production.ini"
# ckanext-archiver initdb
paster --plugin=ckanext-archiver archiver init --config="${APP_DIR}/production.ini"
# ckanext qa initalization
paster --plugin=ckanext-qa qa init --config="${APP_DIR}/production.ini"
# harvester init
paster --plugin=ckanext-harvest harvester initdb --config="${APP_DIR}/production.ini"
