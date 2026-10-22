from unittest.mock import Mock

import pytest
from flask import Flask

from app.routes.location import location
from app.routes.health import health
from app.routes.image import image


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.openapi_spec = Mock()
    app.register_blueprint(location, url_prefix='/v1/location')
    app.register_blueprint(health, url_prefix='/v1/health')
    app.register_blueprint(image, url_prefix='/v1/image')
    app.location_service = Mock()
    app.image_service = Mock()
    return app.test_client()


@pytest.mark.parametrize('value,forced', [(None, False), ('false', False), ('0', False), ('NO', False), ('true', True), ('1', True)])
def test_location_force_api_flags(client, value, forced):
    client.application.location_service.autocomplete_location.return_value = [{'id': 'berlin'}]
    params = {'q': 'Berlin'}
    if value is not None:
        params['force_api'] = value
    response = client.get('/v1/location', query_string=params)
    assert response.status_code == 200
    assert response.json == [{'id': 'berlin'}]
    assert client.application.location_service.autocomplete_location.call_args.kwargs == ({'force_api': True} if forced else {})


def test_health(client):
    assert client.get('/v1/health').json == {'status': 'ok'}


def test_image_stream(client):
    client.application.image_service.get_image_stream.return_value = (b'image bytes', 'image/png')
    response = client.get('/v1/image/events/example.png')
    assert response.status_code == 200
    assert response.data == b'image bytes'
    assert response.mimetype == 'image/png'

