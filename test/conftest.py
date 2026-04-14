from models import *
from sqlalchemy import event
import pytest
from app import create_app


@pytest.fixture()
def app():
    app = create_app({
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'TESTING': True
    })

    with app.app_context():
        @event.listens_for(db.engine, "connect")
        def receive_connect(dbapi_connection, connection_record):
            def collate_ignore(str1, str2):
                return (str1 > str2) - (str1 < str2)
            dbapi_connection.create_collation("SQL_Latin1_General_CP1_CI_AS", collate_ignore)

        @event.listens_for(db.metadata, "before_create")
        def fix_sqlite_defaults(target, connection, **kw):
            for table in target.tables.values():
                for column in table.columns:
                    if column.server_default is not None and hasattr(column.server_default, 'arg'):
                        arg_str = str(column.server_default.arg).lower()
                        if 'getdate' in arg_str:
                            column.server_default = db.DefaultClause(db.text('CURRENT_TIMESTAMP'))
                        elif 'newid' in arg_str:
                            column.server_default = None
                        elif '((1))' in arg_str:
                            column.server_default = db.DefaultClause(db.text('1'))
                        elif '((0))' in arg_str:
                            column.server_default = db.DefaultClause(db.text('0'))

        db.create_all()
        yield app
        db.drop_all()

@pytest.fixture()
def client(app):
    return app.test_client()

@pytest.fixture()
def runner(app):
    return app.test_cli_runner()

@pytest.fixture()
def session(app):
    with app.app_context():
        yield db.session
        db.session.rollback()