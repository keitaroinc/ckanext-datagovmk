FROM keitaro/ckan:2.8.1

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
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-spatial.git@dgm-stable#egg=ckanext-spatial" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-spatial/pip-requirements.txt" && \
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-report.git@dgm-stable#egg=ckanext-report" && \
    # ckanext-qa and related
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-archiver.git@dgm-stable#egg=ckanext-archiver" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-archiver/requirements.txt" && \
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-qa.git@dgm-stable#egg=ckanext-qa" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-qa/requirements.txt" && \
    # showcase
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-showcase.git@dgm-stable#egg=ckanext-showcase" && \
    # harvest
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-harvest.git#egg=ckanext-harvest" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-harvest/pip-requirements.txt" && \
    # c3charts
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-c3charts.git@dgm-stable#egg=ckanext-c3charts" && \
    # disqus
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-disqus.git@dgm-stable#egg=ckanext-disqus" && \
    # dcat
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-dcat.git@dgm-stable#egg=ckanext-dcat" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-dcat/requirements.txt" && \
    # odata
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-odata@dgm-stable#egg=ckanext-odata" && \
    # mk dcat-ap
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-mk_dcatap#egg=ckanext-mk_dcatap" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-mk-dcatap/requirements.txt" && \
    # envvars
    pip install --no-cache-dir -e "git+https://github.com/okfn/ckanext-envvars.git#egg=ckanext-envvars" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-envvars/dev-requirements.txt" && \
    # pages
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-pages.git@dgm-stable#egg=ckanext-pages" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-pages/dev-requirements.txt" && \
    # scheming
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-scheming.git@dgm-stable#egg=ckanext-scheming" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-scheming/requirements.txt" && \
    # repeating
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-repeating.git#egg=ckanext-repeating" && \
    # google analytics
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-googleanalytics.git#egg=ckanext-googleanalytics" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-googleanalytics/requirements.txt" && \
    pip install --no-cache-dir oauth2client && \
    # organogram
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-organogram.git@v0.2#egg=ckanext-organogram" && \
    # validation
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-validation.git@dgm-stable#egg=ckanext-validation" && \
    # skip scheming since we are using a fork
    pip install --no-cache-dir $(cat ${APP_DIR}/src/ckanext-validation/requirements.txt | grep -ivE "ckanext-scheming") && \
    # experience
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-experience.git#egg=ckanext-experience" && \
    # requestdata
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-requestdata.git@dgm-stable#egg=ckanext-requestdata" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-requestdata/requirements.txt" && \
    # likes
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-likes.git#egg=ckanext-likes" && \
    pip install --no-cache-dir -r "${APP_DIR}/src/ckanext-likes/requirements.txt" && \
    # issues
    pip install --no-cache-dir -e "git+https://github.com/keitaroinc/ckanext-issues.git@dgm-stable#egg=ckanext-issues" && \
    # fluent
    pip install --no-cache-dir -e "git+https://github.com/ckan/ckanext-fluent.git#egg=ckanext-fluent"


# Dirty fix for https://github.com/ckan/ckan/issues/3610
#RUN sed -i "s/filename = re.sub(ur'-+', u'-', filename)//g" /srv/app/src/ckan/ckan/lib/munge.py

# These plugins should always be added to cloud instances
# (you can add more needed by your instance)
ENV CKAN__PLUGINS envvars \
                  qa \
                  archiver \
                  datagovmk \
                  report \
                  disqus \
                  stats \
                  text_view \
                  image_view \
                  recline_view \
                  datastore \
                  datapusher \
                  odata \
                  spatial_metadata \
                  spatial_query \
                  showcase \
                  harvest \
                  dcat \
                  dcat_json_interface \
                  structured_data \
                  c3charts \
                  googleanalytics \
                  pages \
                  requestdata \
                  scheming_datasets \
                  scheming_organizations \
                  scheming_groups \
                  repeating \
                  mk_dcatap \
                  organogram \
                  validation \
                  experience \
                  likes \
                  issues \
                  fluent

RUN mkdir -p /var/lib/ckan/default && chown -R ckan:ckan /var/lib/ckan/default
VOLUME /var/lib/ckan/default

# Load envvars plugin on ini file
RUN paster --plugin=ckan config-tool ${APP_DIR}/production.ini "ckan.plugins = ${CKAN__PLUGINS}"

COPY prerun.py /srv/app/prerun.py
COPY extra_scripts.sh /srv/app/extra_scripts.sh

COPY ckan_i18n/mk/ckan.po /srv/app/src/ckan/ckan/i18n/mk/LC_MESSAGES/ckan.po
COPY ckan_i18n/mk/ckan.mo /srv/app/src/ckan/ckan/i18n/mk/LC_MESSAGES/ckan.mo

COPY ckan_i18n/sq/ckan.po /srv/app/src/ckan/ckan/i18n/sq/LC_MESSAGES/ckan.po
COPY ckan_i18n/sq/ckan.mo /srv/app/src/ckan/ckan/i18n/sq/LC_MESSAGES/ckan.mo

RUN sed -i "s/#ckan.storage_path = \/var\/lib\/ckan/ckan.storage_path = \/var\/lib\/ckan\/default/g" /srv/app/production.ini
RUN sed -i "s/#ckan.redis.url = redis:\/\/localhost:6379\/0/ckan.redis.url = redis:\/\/redis.datagovmk:6379\/1/g" /srv/app/production.ini
RUN sed -i "s/\/tmp\/uwsgi.sock --uid 92 --gid 92/\/tmp\/uwsgi.sock/g" /srv/app/start_ckan.sh
RUN sed -i "s/## Site Settings/## Site Settings\nckanext.pages.editor = ckeditor\n/g" /srv/app/production.ini

CMD ["/srv/app/start_ckan.sh"]
