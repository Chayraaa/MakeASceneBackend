from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from authlib.integrations.base_client import MismatchingStateError

from app import create_app
from app.services.password_service import PasswordService


@pytest.fixture(scope='module')
def route_app():
    app = create_app(testing=True)
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    return app


@pytest.fixture
def client(route_app, monkeypatch):
    for name in ('auth_service', 'user_service', 'google_oauth_service', 'tag_service', 'google'):
        monkeypatch.setattr(route_app, name, Mock())
    monkeypatch.setattr(PasswordService, 'verify_token', Mock(return_value=1))
    route_app.user_service.get_user.return_value = SimpleNamespace(id=1, email='a@example.com', mature=True, email_preference=True, role=0, timezone='UTC')
    return route_app.test_client()


@pytest.mark.parametrize('refresh', [False, True])
@pytest.mark.parametrize('success', [False, True])
def test_login_and_refresh(client, refresh, success):
    service = client.application.auth_service
    call = service.refresh_session if refresh else service.authenticate_local
    call.return_value = ('access', 'refresh') if success else None
    payload = {'refresh_token': 'old'} if refresh else {'email': 'a@example.com', 'password': 'test-password'}
    response = client.post('/v1/auth/sessions', json=payload)
    assert response.status_code == (201 if success else 401), response.json
    if success:
        assert response.json['access_token'] == 'access'
    if refresh:
        call.assert_called_once_with('old')
        service.authenticate_local.assert_not_called()
    else:
        call.assert_called_once_with(email='a@example.com', password='test-password')


@pytest.mark.parametrize('path,payload,method,success_code,failure_code', [
    ('/v1/auth/oauth/exchange', {'exchange': 'code'}, 'exchange', 200, 401),
    ('/v1/auth/password/request-reset', {'email': 'a@example.com'}, 'request_password_reset', 200, 500),
    ('/v1/auth/password/reset', {'token': 'reset', 'new_password': 'new-password'}, 'reset_password', 200, 401),
    ('/v1/auth/logout', {}, 'logout', 200, 500),
])
@pytest.mark.parametrize('success', [False, True])
def test_auth_operation_outcomes(client, path, payload, method, success_code, failure_code, success):
    service = client.application.google_oauth_service if method == 'exchange' else client.application.auth_service
    getattr(service, method).return_value = ('access', 'refresh') if success and method == 'exchange' else success
    response = client.post(path, json=payload, headers={'Authorization': 'Bearer test'})
    assert response.status_code == (success_code if success else failure_code), response.json


@pytest.mark.parametrize('success', [False, True])
def test_email_confirmation(client, success):
    client.application.auth_service.confirm_email.return_value = success
    response = client.get('/v1/auth/email/confirm?token=confirm')
    assert response.status_code == (200 if success else 401)
    client.application.auth_service.confirm_email.assert_called_once_with('confirm')


def test_resend_confirmation(client):
    assert client.post('/v1/auth/email/resend', json={'email': 'a@example.com'}).status_code == 200
    client.application.user_service.resend_confirmation_email.assert_called_once_with('a@example.com')


@pytest.mark.parametrize('token,exchange,expected', [(None, None, 400), ({'access_token': 'a'}, None, 400),
    ({'userinfo': {'sub': 'google-id'}}, None, 400), ({'userinfo': {'sub': 'google-id'}}, 'exchange', 201)])
def test_google_callback(client, token, exchange, expected):
    client.application.google.authorize_access_token.return_value = token
    client.application.google_oauth_service.authenticate_user.return_value = exchange
    response = client.get('/v1/auth/oauth/google/callback')
    assert response.status_code == expected, response.json


def test_google_callback_state_mismatch(client):
    client.application.google.authorize_access_token.side_effect = MismatchingStateError()
    response = client.get('/v1/auth/oauth/google/callback')
    assert response.status_code == 400
    assert response.json['error'] == 'oauth_state_mismatch'


@pytest.mark.parametrize('header', [None, 'Basic test', 'Bearer', 'Bearer too many'])
def test_invalid_auth_header_never_loads_user(client, header):
    response = client.get('/v1/users/me', headers={} if header is None else {'Authorization': header})
    # OpenAPI rejects absent/malformed bearer credentials before the decorator.
    assert response.status_code == (401 if header == 'Bearer too many' else 422)
    client.application.user_service.get_user.assert_not_called()


def test_deleted_user_token(client):
    client.application.user_service.get_user.return_value = None
    assert client.get('/v1/users/me', headers={'Authorization': 'Bearer test'}).status_code == 404


def test_user_settings_preserve_false_values(client):
    response = client.patch('/v1/users/me', headers={'Authorization': 'Bearer test'}, json={'mature': False, 'email_preference': False})
    assert response.status_code == 200, response.json
    assert response.json['mature'] is False and response.json['email_preference'] is False
    assert response.json['timezone'] == 'UTC'
    client.application.user_service.update_user.assert_called_once()
