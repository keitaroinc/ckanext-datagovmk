#!/bin/bash

echo "[extra_scripts.sh] Starting ckan workers"
paster --plugin=ckan jobs worker bulk --config="${APP_DIR}/production.ini" -D
paster --plugin=ckan jobs worker priority --config="${APP_DIR}/production.ini" -D
echo "[extra_scripts.sh] Ckan workers started"

