from datetime import datetime
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app import create_app
from app.domain_models.messages.message import Message
from app.services.message_service import MessageService
from app.services.password_service import PasswordService


@pytest.fixture
def message_client(monkeypatch):
    app = create_app(testing=True)
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    app.message_service = Mock()
    app.user_service = Mock()
    app.user_service.get_user.return_value = SimpleNamespace(id=1, role=0)
    monkeypatch.setattr(PasswordService, 'verify_token', Mock(return_value=1))
    return app.test_client()


def test_get_messages(message_client):
    message = Message(user_id=1, title='Title', message='Body', id=4,
                      sent_at=datetime(2026, 10, 26, 12))
    service = message_client.application.message_service
    service.get_messages.return_value = [message]
    response = message_client.get('/v1/users/me/messages?page=2&page_size=5',
                                  headers={'Authorization': 'Bearer test'})
    assert response.status_code == 200
    assert response.json == {'messages': [message.to_dict()]}
    service.get_messages.assert_called_once_with(
        message_client.application.user_service.get_user.return_value, 2, 5)


@pytest.mark.parametrize('read', [True, False])
def test_patch_message(message_client, read):
    service = message_client.application.message_service
    service.mark_message_as_read.return_value = True
    response = message_client.patch('/v1/users/me/messages/4', json={'read': read},
                                    headers={'Authorization': 'Bearer test'})
    assert response.status_code == 200
    assert response.json == {}
    service.mark_message_as_read.assert_called_once_with(
        4, message_client.application.user_service.get_user.return_value, read)


@pytest.mark.parametrize('payload', [{}, {'read': 'false'}, {'read': None}])
def test_patch_rejects_invalid_read(message_client, payload):
    response = message_client.patch('/v1/users/me/messages/4', json=payload,
                                    headers={'Authorization': 'Bearer test'})
    assert response.status_code == 422
    message_client.application.message_service.mark_message_as_read.assert_not_called()


@pytest.mark.parametrize('read', [True, False])
@pytest.mark.parametrize('owner_id', [1, 2, None])
def test_service_update_requires_ownership(read, owner_id):
    repo = Mock()
    message = Message(user_id=owner_id, title='Title', message='Body') if owner_id else None
    repo.get_message_by_id.return_value = message
    repo.update_message.return_value = True
    service = MessageService(repo, Mock(), Mock())
    assert service.mark_message_as_read(4, SimpleNamespace(id=1), read) is (True if owner_id == 1 else None)
    if owner_id == 1:
        assert message.read is read
        repo.update_message.assert_called_once_with(message)
    else:
        repo.update_message.assert_not_called()


@pytest.mark.parametrize('method,service_method', [
    ('patch', 'mark_message_as_read'), ('delete', 'delete_message'),
])
@pytest.mark.parametrize('result,status', [(True, 200), (None, 404), (False, 500)])
def test_message_write_statuses(message_client, method, service_method, result, status):
    call = getattr(message_client.application.message_service, service_method)
    call.return_value = result
    response = getattr(message_client, method)(
        '/v1/users/me/messages/4', headers={'Authorization': 'Bearer test'},
        **({'json': {'read': False}} if method == 'patch' else {}))
    assert response.status_code == status
    user = message_client.application.user_service.get_user.return_value
    call.assert_called_once_with(*((4, user, False) if method == 'patch' else (4, user)))


@pytest.mark.parametrize('method,path', [
    ('get', '/v1/users/me/messages'),
    ('patch', '/v1/users/me/messages/4'),
    ('delete', '/v1/users/me/messages/4'),
])
def test_message_routes_require_authentication(message_client, method, path):
    response = getattr(message_client, method)(
        path, **({'json': {'read': True}} if method == 'patch' else {}))
    assert response.status_code == 401


@pytest.mark.parametrize('query,status', [('', 500), ('?page=0', 422),
                                         ('?page_size=-1', 422), ('?page=abc', 422)])
def test_message_list_errors(message_client, query, status):
    message_client.application.message_service.get_messages.return_value = None
    response = message_client.get('/v1/users/me/messages' + query,
                                  headers={'Authorization': 'Bearer test'})
    assert response.status_code == status


@pytest.mark.parametrize('owner_id', [1, 2, None])
@pytest.mark.parametrize('write_result', [True, False])
def test_delete_service_results(owner_id, write_result):
    repo = Mock()
    repo.get_message_by_id.return_value = (
        Message(user_id=owner_id, title='Title', message='Body') if owner_id else None)
    repo.delete_message.return_value = write_result
    service = MessageService(repo, Mock(), Mock())
    assert service.delete_message(4, SimpleNamespace(id=1)) is (
        write_result if owner_id == 1 else None)
    if owner_id != 1:
        repo.delete_message.assert_not_called()


def test_update_service_write_failure():
    repo = Mock()
    repo.get_message_by_id.return_value = Message(user_id=1, title='Title', message='Body')
    repo.update_message.return_value = False
    service = MessageService(repo, Mock(), Mock())
    assert service.mark_message_as_read(4, SimpleNamespace(id=1), False) is False
