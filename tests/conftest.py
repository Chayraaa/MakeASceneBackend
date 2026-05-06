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
        db.drop_all()

@pytest.fixture
def session(app):
    return db.session