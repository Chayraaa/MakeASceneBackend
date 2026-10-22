from types import SimpleNamespace

import pytest

from app.repositories.storage.auth.sql_confirm_token_repo import SqlConfirmTokenRepo
from app.repositories.storage.auth.sql_password_reset_token_repo import SqlPasswordResetTokenRepo
from app.repositories.storage.auth.sql_refresh_token_repo import SqlRefreshTokenRepo
from app.repositories.storage.sql_user_repo import SqlUserRepo


@pytest.mark.parametrize('repo_type', [SqlConfirmTokenRepo, SqlPasswordResetTokenRepo, SqlRefreshTokenRepo])
def test_token_lifecycle_and_isolation(session, repo_type):
    users = SqlUserRepo(session)
    users.create_user('first@example.com', 'hash')
    users.create_user('second@example.com', 'hash')
    first = users.get_user_by_email('first@example.com')
    second = users.get_user_by_email('second@example.com')
    repo = repo_type(session)
    assert repo.get_by_token_hash('missing') is None
    assert not repo.revoke(SimpleNamespace(id=999))
    assert repo.create('first-hash', first)
    assert not repo.create('first-hash', first)
    assert repo.create('second-hash', second)
    token = repo.get_by_token_hash('first-hash')
    assert token.user_id == first.id
    assert token.hashed_token == 'first-hash'
    assert token.expires_at > token.created_at
    assert token.revoked is False
    if hasattr(repo, 'get_by_user'):
        assert [t.id for t in repo.get_by_user(first)] == [token.id]
    assert repo.revoke(token)
    assert repo.get_by_token_hash('first-hash').revoked is True
    assert repo.get_by_token_hash('second-hash').revoked is False
