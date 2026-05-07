from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.auth_service import AuthService


def test_valid_auth():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    user = MagicMock()
    user.oauth = "local"
    user.hashed_password = "hashed"
    user.id = 123

    user_repo.get_user_by_email.return_value = user

    service = AuthService(user_repo, refresh_repo)

    with patch("app.services.auth_service.PasswordService.verify_password", return_value=True), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="refresh"), \
            patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh") as mock_hash:
        res = service.authenticate_local("test@test.com", "test")

    mock_hash.assert_called_once_with("refresh")
    refresh_repo.create.assert_called_once_with(hashed_token="hashed_refresh", user=user)
    assert res == ("token", "refresh")


def test_invalid_password():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    user = MagicMock()
    user.oauth = "local"
    user_repo.get_user_by_email.return_value = user

    service = AuthService(user_repo, refresh_repo)
    with patch("app.services.auth_service.PasswordService.verify_password", return_value=False):
        res = service.authenticate_local("test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_invalid_oauth():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    user = MagicMock()
    user.oauth = "google"

    user_repo.get_user_by_email.return_value = user
    service = AuthService(user_repo, refresh_repo)
    res = service.authenticate_local("test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_non_existing_user():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    user_repo.get_user_by_email.return_value = None

    service = AuthService(user_repo, refresh_repo)
    res = service.authenticate_local("test.test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_valid():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    session = MagicMock()
    session.revoked = False
    session.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
    session.user_id = 123

    refresh_repo.get_by_token_hash.return_value = session

    service = AuthService(user_repo, refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="new_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_called_once_with(session)
    refresh_repo.create.assert_called_once()
    assert res == ("token", "new_refresh")


def test_refresh_session_revoked():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    session = MagicMock()
    session.revoked = True

    refresh_repo.get_by_token_hash.return_value = session

    service = AuthService(user_repo, refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_expired():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    session = MagicMock()
    session.revoked = False
    session.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)

    refresh_repo.get_by_token_hash.return_value = session

    service = AuthService(user_repo, refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_not_found():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    refresh_repo.get_by_token_hash.return_value = None

    service = AuthService(user_repo, refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None