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
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-c3charts.git#egg=ckanext-c3charts" && \
    # disqus
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-disqus#egg=ckanext-disqus" && \
    # dcat
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-dcat/requirements.txt" && \
    # odata
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-odata@odata-ckan-2.8#egg=ckanext-odata" && \
    # mk dcat-ap
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-mk_dcatap#egg=ckanext-mk_dcatap" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-mk-dcatap/requirements.txt"
    


# Dirty fix for https://github.com/ckan/ckan/issues/3610
#RUN sed -i "s/filename = re.sub(ur'-+', u'-', filename)//g" /srv/app/src/ckan/ckan/lib/munge.py

# These plugins should always be added to cloud instances
# (you can add more needed by your instance)
ENV CKAN__PLUGINS disqus \
                  stats \
                  text_view \
                  image_view \
                  recline_view \
                  odata \
                  spatial_metadata \
                  spatial_query \
                  geo_view \
                  geojson_view \
                  qa \
                  archiver \
                  report \
                  showcase \
                  harvest \
                  ckan_harvester \
                  dcat \
                  dcat_rdf_harvester \
                  dcat_json_harvester \
                  dcat_json_interface \
                  structured_data \
                  c3charts \
                  mk_dcatap


USER ckan
# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"
# configure spatial to use solr as search backend
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckanext.spatial.search_backend = solr"
# ckanext-archiver configuration
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckanext-archiver.cache_url_root = http://example.com"

# ckanext-harverst
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.harvest.mq.type = redis"

# disqus - set up the real doman here (match with the domain set up at disqus.com)
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "disqus.name = data.gov.mk"

# DCAT profiles
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckanext.dcat.rdf.profiles = euro_dcat_ap mk_dcat_ap"

# Locale configuration
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini " ckan.locales_offered = mk"

CMD ["/srv/app/start_ckan.sh"]
