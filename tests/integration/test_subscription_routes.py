from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import yaml
from flask import Flask
from openapi_core import OpenAPI

from app.routes.user import users
from app.services.password_service import PasswordService


@pytest.fixture(params=[("event", "events"), ("site_account", "site_accounts")])
def subscription_client(request, monkeypatch):
    kind, plural = request.param
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


def test_subscription_gets(subscription_client):
    client, kind, plural, service, user = subscription_client
    subscription = SimpleNamespace(notifications_enabled=False, **{kind + "_id": 7})
    getattr(service, f"get_{kind}_subscription").return_value = subscription
    response = client.get(f"/v1/users/me/{plural}/7", headers=AUTH)
    assert response.status_code == 200
    assert response.json == {"id": 7, "notify": False}
    getattr(service, f"get_{kind}_subscription").assert_called_once_with(user, 7)
    getattr(service, f"get_{kind}_subscriptions").return_value = [subscription]
    response = client.get(f"/v1/users/me/{plural}?page=2&page_size=5", headers=AUTH)
    assert response.status_code == 200
    assert response.json == [{"id": 7, "notify": False}]
    getattr(service, f"get_{kind}_subscriptions").assert_called_once_with(user, 2, 5)


@pytest.mark.parametrize("method,prefix", [("post", "subscribe_to"), ("delete", "unsubscribe_from"), ("patch", "set")])
@pytest.mark.parametrize("result,status", [(True, 200), (False, 500), (None, 404)])
def test_subscription_write_responses(subscription_client, method, prefix, result, status):
    client, kind, plural, service, user = subscription_client
    name = f"set_{kind}_notifications" if method == "patch" else f"{prefix}_{kind}"
    call = getattr(service, name)
    call.return_value = result
    response = getattr(client, method)(f"/v1/users/me/{plural}/7", headers=AUTH,
        **({"json": {"notify": False}} if method == "patch" else {}))
    assert response.status_code == status
    call.assert_called_once_with(*((user, 7, False) if method == "patch" else (user, 7)))
    if status == 200:
        assert "message" in response.json


@pytest.mark.parametrize("method,suffix", [("get", ""), ("get", "/7"), ("post", "/7"), ("patch", "/7"), ("delete", "/7")])
def test_subscription_authentication(subscription_client, method, suffix):
    client, _, plural, service, _ = subscription_client
    response = getattr(client, method)(f"/v1/users/me/{plural}{suffix}")
    assert response.status_code == 401
    assert service.mock_calls == []


@pytest.mark.parametrize("payload", [{}, {"notify": "false"}, {"notify": None}])
def test_invalid_notification_payload(subscription_client, payload):
    client, _, plural, service, _ = subscription_client
    response = client.patch(f"/v1/users/me/{plural}/7", headers=AUTH, json=payload)
    assert response.status_code == 422
    assert service.mock_calls == []


@pytest.mark.parametrize("query", ["page=0", "page_size=-1", "page=abc"])
def test_invalid_subscription_pagination(subscription_client, query):
    client, _, plural, service, _ = subscription_client
    assert client.get(f"/v1/users/me/{plural}?{query}", headers=AUTH).status_code == 422
    assert service.mock_calls == []


def test_subscription_read_failures(subscription_client):
    client, kind, plural, service, _ = subscription_client
    getattr(service, f"get_{kind}_subscription").return_value = None
    assert client.get(f"/v1/users/me/{plural}/7", headers=AUTH).status_code == 404
    getattr(service, f"get_{kind}_subscriptions").return_value = None
    assert client.get(f"/v1/users/me/{plural}", headers=AUTH).status_code == 500
    getattr(service, f"get_{kind}_subscriptions").return_value = []
    response = client.get(f"/v1/users/me/{plural}", headers=AUTH)
    assert response.status_code == 200
    assert response.json == []
