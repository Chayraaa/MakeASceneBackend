from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml
from flask import Flask
from openapi_core import OpenAPI

from app.routes.user import users
from app.services.password_service import PasswordService


@pytest.fixture
def subscription_client(monkeypatch):
    kind, plural = "location", "locations"
    app = Flask(__name__)
    app.config.update(TESTING=True, SERVER_NAME="127.0.0.1:5000")
    spec = yaml.safe_load(Path("app/static/makeascene.openapi.yaml").read_text(encoding="utf-8"))
    app.openapi_spec = OpenAPI.from_dict(spec)
    app.user_service = Mock()
    user = SimpleNamespace(id=1, role=0)
    app.user_service.get_user.return_value = user
    service = Mock()
    setattr(app, kind + "_service", service)
    app.register_blueprint(users, url_prefix="/v1/users")
    monkeypatch.setattr(PasswordService, "verify_token", Mock(return_value=1))
    return app.test_client(), kind, plural, service, user


AUTH = {"Authorization": "Bearer test"}


@pytest.mark.parametrize("method,prefix", [("post", "subscribe_to"), ("delete", "unsubscribe_from")])
@pytest.mark.parametrize("result,status", [(True, 200), (False, 500), (None, 404)])
def test_location_write_responses(subscription_client, method, prefix, result, status):
    client, _, _, service, user = subscription_client
    call = getattr(service, f"{prefix}_location")
    call.return_value = result
    response = getattr(client, method)("/v1/users/me/locations/place-123", headers=AUTH)
    assert response.status_code == status
    call.assert_called_once_with(user, "place-123")


def test_location_list(subscription_client):
    client, _, _, service, user = subscription_client
    locations = [{"id": "place-123", "name": "Berlin", "formatted": "Berlin, Germany", "lat": 52.5, "lon": 13.4}]
    service.get_saved_locations.return_value = locations
    response = client.get("/v1/users/me/locations?page=2&page_size=5", headers=AUTH)
    assert response.status_code == 200
    assert response.json == {"locations": locations}
    service.get_saved_locations.assert_called_once_with(user, 2, 5)
    service.get_saved_locations.return_value = []
    assert client.get("/v1/users/me/locations", headers=AUTH).json == {"locations": []}
    service.get_saved_locations.return_value = None
    assert client.get("/v1/users/me/locations", headers=AUTH).status_code == 500


@pytest.mark.parametrize("method,suffix", [("get", ""), ("post", "/place-123"), ("delete", "/place-123")])
def test_location_authentication(subscription_client, method, suffix):
    client, _, _, service, _ = subscription_client
    assert getattr(client, method)(f"/v1/users/me/locations{suffix}").status_code == 401
    assert service.mock_calls == []


@pytest.mark.parametrize("query", ["page=0", "page_size=-1", "page=abc"])
def test_invalid_location_pagination(subscription_client, query):
    client, _, _, service, _ = subscription_client
    assert client.get(f"/v1/users/me/locations?{query}", headers=AUTH).status_code == 422
    assert service.mock_calls == []
