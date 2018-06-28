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
            python2-dev \
            openssl-dev


# Install our extension
RUN pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-datagovmk.git#egg=ckanext-datagovmk" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-datagovmk/requirements.txt" && \
    # Install extensions
    # ckanext-spatial and related
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-spatial.git@ckan-2.8#egg=ckanext-spatial" && \
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
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-mk-dcatap/requirements.txt" && \
    # envvars
    pip install --no-cache-dir -e "git+https://github.com/okfn/ckanext-envvars.git#egg=ckanext-envvars" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-envvars/dev-requirements.txt" && \
    # pages
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-pages.git@news#egg=ckanext-pages" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-pages/dev-requirements.txt" && \
    # scheming
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-scheming.git#egg=ckanext-scheming" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-scheming/requirements.txt" && \
    # repeating
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-repeating.git#egg=ckanext-repeating" && \
    # google analytics
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-googleanalytics.git#egg=ckanext-googleanalytics" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-googleanalytics/requirements.txt" && \
    pip install --no-cache-dir oauth2client



# Dirty fix for https://github.com/ckan/ckan/issues/3610
#RUN sed -i "s/filename = re.sub(ur'-+', u'-', filename)//g" /srv/app/src/ckan/ckan/lib/munge.py

# These plugins should always be added to cloud instances
# (you can add more needed by your instance)
ENV CKAN__PLUGINS envvars \
                  disqus \
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
                  googleanalytics \
                  pages \
                  datagovmk \
                  scheming_datasets \
                  repeating \
                  mk_dcatap

RUN mkdir -p /var/lib/ckan/default && chown -R ckan:ckan /var/lib/ckan/default
VOLUME /var/lib/ckan/default

# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"

COPY prerun.py /srv/app/prerun.py

RUN sed -i "s/#ckan.storage_path = \/var\/lib\/ckan/ckan.storage_path = \/var\/lib\/ckan\/default/g" /srv/app/production.ini
RUN sed -i "s/#ckan.redis.url = redis:\/\/localhost:6379\/0/ckan.redis.url = redis:\/\/redis.datagovmk:6379\/1/g" /srv/app/production.ini

CMD ["/srv/app/start_ckan.sh"]
