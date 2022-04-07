import pytest

from ckan.lib.search import rebuild

from ckanext.googleanalytics.dbutil import init_tables as init_tables_ga
from ckanext.datagovmk.model.user_authority \
    import setup as setup_user_authority_table
from ckanext.datagovmk.model.user_authority_dataset \
    import setup as setup_user_authority_dataset_table
from ckanext.c3charts.model.featured_charts \
    import setup as setup_featured_charts_table
from ckanext.datagovmk.model.most_active_organizations \
    import setup as setup_most_active_organizations_table

@pytest.fixture
def dgm_setup():
    init_tables_ga()
    setup_user_authority_table()
    setup_user_authority_dataset_table()
    setup_featured_charts_table()
    setup_most_active_organizations_table()
    rebuild()
