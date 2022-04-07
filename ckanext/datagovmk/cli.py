import click
from flask import Flask
import ckanext.datagovmk.commands as commands


def get_commands():

    @click.group()
    def datagovmk():
        """Generates datagovmk command"""
        pass

    @datagovmk.command()
    def initdb():
        commands.tables_init()
        click.secho(u'Datagovmk tables are setup', fg=u"green")

    @datagovmk.command()
    def setup_stats_tables():
        from ckanext.datagovmk.model.stats import _setup_stats_tables
        _setup_stats_tables()

    @datagovmk.command()
    def fetch_most_active_orgs():
        app = Flask(__name__)
        with app.test_request_context():
            commands.fetch_most_active_orgs()

    @datagovmk.command()
    def check_outdated_datasets():
        app = Flask(__name__)
        with app.test_request_context():
            commands._processl_all_datasets()

    return [datagovmk]
