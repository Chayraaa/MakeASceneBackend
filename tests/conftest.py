from pathlib import Path

import pytest
from dotenv import load_dotenv

env_path = Path(__file__).resolve().parent.parent / "test.env"
load_dotenv(env_path)

from app import create_app, db

@pytest.fixture
def app():
    app = create_app(testing=True)

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

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