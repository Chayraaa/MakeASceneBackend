import pytest
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