from pathlib import Path

import pytest
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, LargeBinary, MetaData, String, Table

env_path = Path(__file__).resolve().parent.parent / "test.env"
load_dotenv(env_path)

from app import create_app, db

@pytest.fixture
def app():
    app = create_app(testing=True)

    with app.app_context():
        # Ordinary repository tests use SQLite without SpatiaLite. Keep the
        # location table/FK available, but test spatial operations in PostGIS.
        locations = Table(
            "locations", MetaData(),
            Column("id", Integer, primary_key=True),
            Column("place_id", String, nullable=False, unique=True),
            Column("details", String, nullable=False),
            Column("geometry", LargeBinary, nullable=True),
        )
        tables = [table for table in db.metadata.sorted_tables if table.name != "locations"]
        locations.create(db.engine)
        db.metadata.create_all(db.engine, tables=tables)
        try:
            yield app
        finally:
            db.session.remove()
            db.metadata.drop_all(db.engine, tables=tables)
            locations.drop(db.engine)

@pytest.fixture
def session(app):
    with app.app_context():
        connection = db.engine.connect()
        transaction = connection.begin()

        session = db.session

        session.bind = connection

        yield session

        session.rollback()
        transaction.rollback()
        connection.close()
        session.remove()
