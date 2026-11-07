import pytest

from app.database_models.user_model import UserModel
from app.services.password_service import PasswordService


@pytest.fixture
def users_client(app, monkeypatch):
    from app.extensions import db
    app.config['SERVER_NAME'] = '127.0.0.1:5000'
    with app.app_context():
        db.session.add_all([
            UserModel(id=1, email='actor@example.com', password='hashed'),
            UserModel(id=2, email='target@example.com', password='hashed'),
        ])
        db.session.commit()
    monkeypatch.setattr(PasswordService, 'verify_token', lambda token: 1)
    return app.test_client()


def set_role(client, role):
    from app.extensions import db
    with client.application.app_context():
        db.session.get(UserModel, 1).role = role
        db.session.commit()


def target(client):
    with client.application.app_context():
        return client.application.user_service.get_user(2)


HEADERS = {'Authorization': 'Bearer test'}


@pytest.mark.parametrize('role', [0, 1, 2])
@pytest.mark.parametrize('operation', ['search', 'confirm', 'delete', 'role'])
def test_moderation_permissions_and_persistence(users_client, role, operation):
    set_role(users_client, role)
    if operation == 'search':
        response = users_client.get('/v1/users?q=TARGET', headers=HEADERS)
    elif operation == 'delete':
        response = users_client.delete('/v1/users/2', headers=HEADERS)
    else:
        payload = {'email-accepted': True} if operation == 'confirm' else {'role': 1, 'email-accepted': True}
        response = users_client.patch('/v1/users/2', json=payload, headers=HEADERS)
    allowed = role >= (2 if operation == 'role' else 1)
    assert response.status_code == (200 if allowed else 401)
    user = target(users_client)
    if not allowed:
        assert user is not None and user.role == 0 and user.confirmed is False
    elif operation == 'search':
        assert [item['id'] for item in response.json] == [2]
        assert response.json[0]['role'] == 0
        assert 'hashed_password' not in response.json[0]
    elif operation == 'delete':
        assert user is None
    else:
        assert user.confirmed is True
        assert user.role == (1 if operation == 'role' else 0)
        assert response.json['role'] == user.role


@pytest.mark.parametrize('method,path,payload', [
    ('get', '/v1/users', None),
    ('patch', '/v1/users/2', {'email-accepted': True}),
    ('delete', '/v1/users/2', None),
])
def test_moderation_requires_authentication(users_client, method, path, payload):
    response = getattr(users_client, method)(path, **({'json': payload} if payload else {}))
    assert response.status_code == 401
    assert target(users_client).confirmed is False


@pytest.mark.parametrize('payload', [{'role': -1}, {'role': 3}, {'role': '1'}, {'role': True}, {'role': None}, {'email-accepted': 'yes'}])
def test_invalid_moderation_payload(users_client, payload):
    set_role(users_client, 2)
    response = users_client.patch('/v1/users/2', json=payload, headers=HEADERS)
    assert response.status_code == 422
    assert target(users_client).role == 0
    assert target(users_client).confirmed is False


@pytest.mark.parametrize('method', ['patch', 'delete'])
def test_missing_target(users_client, method):
    set_role(users_client, 1)
    response = getattr(users_client, method)('/v1/users/999', headers=HEADERS,
                                           **({'json': {'email-accepted': True}} if method == 'patch' else {}))
    assert response.status_code == 404


def test_self_responses_include_role_and_cannot_escalate(users_client):
    assert users_client.get('/v1/users/me', headers=HEADERS).json['role'] == 0
    response = users_client.patch('/v1/users/me', json={'mature': False, 'role': 2}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json['role'] == 0
    assert response.json['mature'] is False


def test_search_treats_wildcards_literally(users_client):
    set_role(users_client, 1)
    assert users_client.get('/v1/users?q=%25', headers=HEADERS).json == []
    assert len(users_client.get('/v1/users', headers=HEADERS).json) == 2


@pytest.mark.parametrize('role', [0, 1, 2])
def test_admin_can_assign_each_role_without_confirming_email(users_client, role):
    set_role(users_client, 2)
    response = users_client.patch('/v1/users/2', json={'role': role}, headers=HEADERS)
    assert response.status_code == 200
    assert target(users_client).role == role
    assert target(users_client).confirmed is False


def test_moderator_can_revoke_confirmation(users_client):
    set_role(users_client, 1)
    for confirmed in [True, False]:
        response = users_client.patch('/v1/users/2', json={'email-accepted': confirmed}, headers=HEADERS)
        assert response.status_code == 200
        assert target(users_client).confirmed is confirmed


def test_search_paginates_filtered_results(users_client):
    from app.extensions import db
    with users_client.application.app_context():
        db.session.add(UserModel(id=3, email='target-second@example.com', password='hashed'))
        db.session.commit()
    set_role(users_client, 1)
    for page, expected in [(1, [2]), (2, [3]), (3, [])]:
        response = users_client.get(f'/v1/users?q=target&page={page}&page-size=1', headers=HEADERS)
        assert response.status_code == 200
        assert [user['id'] for user in response.json] == expected


def test_search_defaults_to_25_users(users_client):
    from app.extensions import db
    with users_client.application.app_context():
        db.session.add_all(UserModel(id=i, email=f'user{i}@example.com', password='hashed')
                           for i in range(3, 29))
        db.session.commit()
    set_role(users_client, 1)
    response = users_client.get('/v1/users', headers=HEADERS)
    assert response.status_code == 200
    assert [user['id'] for user in response.json] == list(range(1, 26))
    response = users_client.get('/v1/users?page=2', headers=HEADERS)
    assert [user['id'] for user in response.json] == [26, 27, 28]


@pytest.mark.parametrize('query', ['page=0', 'page=-1', 'page=abc', 'page=1.5',
                                  'page-size=0', 'page-size=-1', 'page-size=abc', 'page-size=1.5'])
def test_search_rejects_invalid_pagination(users_client, query):
    set_role(users_client, 1)
    response = users_client.get(f'/v1/users?{query}', headers=HEADERS)
    assert response.status_code == 422
