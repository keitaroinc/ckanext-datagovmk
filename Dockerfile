FROM keitaro/ckan:2.8.0

MAINTAINER Keitaro <info@keitaro.com>

USER root

RUN apk add --update-cache \
            --repository http://dl-3.alpinelinux.org/alpine/edge/testing/ \
            --allow-untrusted \
            geos \
            geos-dev
RUN apk add bash \
            g++ \
            gcc \
            libffi-dev \
            libstdc++ \
            libxml2 \
            libxml2-dev \
            libxslt \
            libxslt-dev \
            make \
            musl-dev \
            pcre \
            python2-dev


# Install our extension
RUN pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-datagovmk.git#egg=ckanext-datagovmk" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-datagovmk/requirements.txt" && \
    # Install extensions
    # ckanext-spatial and related
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-spatial.git#egg=ckanext-spatial" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-spatial/pip-requirements.txt" && \
    pip install --no-cache-dir ckanext-geoview && \
    pip install --no-cache-dir -e "git+https://github.com/datagovuk/ckanext-report.git#egg=ckanext-report" && \
    # ckanext-qa and related
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-archiver.git@ckan_2.8_celery_compat#egg=ckanext-archiver" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-archiver/requirements.txt" && \
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-qa.git@ckan_2.8_compat#egg=ckanext-qa" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-qa/requirements.txt" && \
    # showcase
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-showcase.git#egg=ckanext-showcase" && \
    #  harvest
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-harvest/pip-requirements.txt" && \
    # c3charts
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-c3charts.git#egg=ckanext-c3charts"



# Dirty fix for https://github.com/ckan/ckan/issues/3610
#RUN sed -i "s/filename = re.sub(ur'-+', u'-', filename)//g" /srv/app/src/ckan/ckan/lib/munge.py

# These plugins should always be added to cloud instances
# (you can add more needed by your instance)
ENV CKAN__PLUGINS stats text_view image_view recline_view spatial_metadata spatial_query geo_view geojson_view qa archiver report showcase harvest ckan_harvester c3charts

USER ckan
# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"
# configure spatial to use solr as search backend
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckanext.spatial.search_backend = solr"
# ckanext-archiver configuration
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckanext-archiver.cache_url_root = http://example.com"

# ckanext-harverst
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.harvest.mq.type = redis"


CMD ["/srv/app/start_ckan.sh"]