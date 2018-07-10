.. You should enable this project on travis-ci.org and coveralls.io to make
   these badges work. The necessary Travis and Coverage config files have been
   generated for you.

.. image:: https://travis-ci.org//ckanext-datagovmk.svg?branch=master
    :target: https://travis-ci.org//ckanext-datagovmk

.. image:: https://coveralls.io/repos//ckanext-datagovmk/badge.svg
  :target: https://coveralls.io/r//ckanext-datagovmk

.. image:: https://pypip.in/download/ckanext-datagovmk/badge.svg
    :target: https://pypi.python.org/pypi//ckanext-datagovmk/
    :alt: Downloads

.. image:: https://pypip.in/version/ckanext-datagovmk/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-datagovmk/
    :alt: Latest Version

.. image:: https://pypip.in/py_versions/ckanext-datagovmk/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-datagovmk/
    :alt: Supported Python versions

.. image:: https://pypip.in/status/ckanext-datagovmk/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-datagovmk/
    :alt: Development Status

.. image:: https://pypip.in/license/ckanext-datagovmk/badge.svg
    :target: https://pypi.python.org/pypi/ckanext-datagovmk/
    :alt: License

=============
ckanext-datagovmk
=============

.. Put a description of your extension here:
   What does it do? What features does it have?
   Consider including some screenshots or embedding a video!


------------
Requirements
------------

For example, you might want to mention here which versions of CKAN this
extension works with.


---------------------
Install prerequisites
---------------------

This extension requires other extensions to be installed prior to installation and
configuring for CKAN.

To install these dependecies you must first activate your CKAN virtual
environment::

     . /usr/lib/ckan/default/bin/activate


Then proceed to install the extensions bellow.


ckanext-scheming
^^^^^^^^^^^^^^^^

Install scheming and its dependencies with the patch for CKAN 2.8::

    pip install -se "git+https://github.com/keitaroinc/ckanext-scheming.git@ckan-2.8#egg=ckanext-scheming"
    pip install -r /usr/lib/ckan/default/src/ckanext-scheming/requirements.txt



ckanext-repeating
^^^^^^^^^^^^^^^^^

This plays with ckanext-scheming and adds support for repeatable fields::

    pip install +e "git+https://github.com/keitaroinc/ckanext-repeating.git#egg=ckanext-repeating"




ckanext-dcat
^^^^^^^^^^^^

This extension enabes CKAN to process and export catalogs and datasets metadata in
accordance with the DCAT standard.

Install it along with its dependencies::

    pip install -e "git+https://github.com/ckan/ckanext-dcat.git#egg=ckanext-dcat"
    pip install -r /usr/lib/ckan/default/src/ckanext-dcat/requirements.txt



ckanext-mk_dcatap
^^^^^^^^^^^^^^^^^

Macedonian DCAT Application Profile specs and Scheming schema definition to support
this profile.

Install it::

    pip install -e "git+https://github.com/keitaroinc/ckanext-mk_dcatap#egg=ckanext-mk_dcatap"
    pip install -r /usr/lib/ckan/default/src/ckanext-mk-dcatap/requirements.txt


To enable schemig with the MK DCAT profile, you'll need to add the following propeties
in CKAN configuration file (.ini)::

    # Scheming
    scheming.dataset_schemas=ckanext.mk_dcatap:mk_dcatap_schema.json

    scheming.presets = ckanext.scheming:presets.json
                       ckanext.repeating:presets.json

    # Enable the DCAP profile
    ckanext.dcat.rdf.profiles = mk_dcat_ap


Add the extensions to ``ckan.plugins``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Add the extensions to the ``ckan.plugins`` setting in your CKAN config file (by default
the config file is located at ``/etc/ckan/default/production.ini``).
The order of the plugins matters in this case. You must put ``scheming_datasets`` **after**
``datagovmk``, and ``repeating`` should be placed after ``schemig_datasets``. ``mk_dcatap``
goes at the end.

The plugins list should look something like this::

    ckan.plugins = <other plugins> dcat datagovmk scheming_datasets repeating  mk_dcatap 



------------
Installation
------------

.. Add any additional install steps to the list below.
   For example installing any non-Python dependencies or adding any required
   config settings.

To install ckanext-datagovmk:

1. Activate your CKAN virtual environment, for example::

     . /usr/lib/ckan/default/bin/activate

2. Install the ckanext-datagovmk Python package into your virtual environment::

     pip install ckanext-datagovmk

3. Add ``datagovmk`` to the ``ckan.plugins`` setting in your CKAN
   config file (by default the config file is located at
   ``/etc/ckan/default/production.ini``).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu::

     sudo service apache2 reload

5. Copy solr schema::

    cp solr/schema.xml /opt/solr/server/solr/ckan/conf/schema.xml


---------------
Config Settings
---------------

Additional configuration settings::

    # Openstreetmap Overpass API URL.
    # (optional, default: https://lz4.overpass-api.de/api/interpreter).
    ckanext.datagovmk.osm_overpass_url = https://lz4.overpass-api.de/api/interpreter


------------------------
Development Installation
------------------------

To install ckanext-datagovmk for development, activate your CKAN virtualenv and
do::

    git clone https://github.com//ckanext-datagovmk.git
    cd ckanext-datagovmk
    python setup.py develop
    pip install -r dev-requirements.txt


-----------------
Running the Tests
-----------------

To run the tests, do::

    nosetests --nologcapture --with-pylons=test.ini

To run the tests and produce a coverage report, first make sure you have
coverage installed in your virtualenv (``pip install coverage``) then run::

    nosetests --nologcapture --with-pylons=test.ini --with-coverage --cover-package=ckanext.datagovmk --cover-inclusive --cover-erase --cover-tests


---------------------------------
Registering ckanext-datagovmk on PyPI
---------------------------------

ckanext-datagovmk should be availabe on PyPI as
https://pypi.python.org/pypi/ckanext-datagovmk. If that link doesn't work, then
you can register the project on PyPI for the first time by following these
steps:

1. Create a source distribution of the project::

     python setup.py sdist

2. Register the project::

     python setup.py register

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the first release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.1 then do::

       git tag 0.0.1
       git push --tags


----------------------------------------
Releasing a New Version of ckanext-datagovmk
----------------------------------------

ckanext-datagovmk is availabe on PyPI as https://pypi.python.org/pypi/ckanext-datagovmk.
To publish a new version to PyPI follow these steps:

1. Update the version number in the ``setup.py`` file.
   See `PEP 440 <http://legacy.python.org/dev/peps/pep-0440/#public-version-identifiers>`_
   for how to choose version numbers.

2. Create a source distribution of the new version::

     python setup.py sdist

3. Upload the source distribution to PyPI::

     python setup.py sdist upload

4. Tag the new release of the project on GitHub with the version number from
   the ``setup.py`` file. For example if the version number in ``setup.py`` is
   0.0.2 then do::

       git tag 0.0.2
       git push --tags


-------------------------------------
Building and running the docker image
-------------------------------------

To build the docker image, run the following::

    docker build -t keitaro/datagovmk:latest .


To run the docker instance (assuming you have PostgreSQL and Solr servers already running on your computer)::

    HOST_IP=$(hostname -I |cut -f1 -d' ')
    docker run -it -e CKAN_SQLALCHEMY_URL=postgresql://ckan_default:ckan_default@${HOST_IP}/ckan_default \
                   -e CKAN_SOLR_URL=http://${HOST_IP}:8983/solr/ckan \
                   -e CKAN__REDIS__URL="redis://${HOST_IP}:6379/1"\
                   -p 5000:5000 keitaro/datagovmk:latest