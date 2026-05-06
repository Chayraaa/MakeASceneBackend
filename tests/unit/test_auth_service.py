from unittest.mock import MagicMock, patch

from sqlalchemy.ext.asyncio import result

from app.services.auth_service import AuthService


def test_valid_auth():
    repo = MagicMock()

    user = MagicMock()
    user.oauth = "local"
    user.hashed_password = "hashed"
    user.id = 123

    repo.get_user_by_email.return_value = user

    service = AuthService(repo)

    with patch("app.services.auth_service.PasswordService.verify_password", return_value=True), \
            patch("app.services.auth_service.PasswordService.generate_token", return_value="token"):
        res = service.authenticate_local("test@test.com", "test")

    assert res == "token"


def test_invalid_password():
    repo = MagicMock()
    user = MagicMock()
    user.oauth = "local"
    repo.get_user_by_email.return_value = user

    service = AuthService(repo)
    with patch("app.services.auth_service.PasswordService.verify_password", return_value=False):
        res = service.authenticate_local("test@test.com", "test")

    assert res is None


def test_invalid_oauth():
    repo = MagicMock()
    user = MagicMock()
    user.oauth = "google"

    repo.get_user_by_email.return_value = user
    service = AuthService(repo)
    res = service.authenticate_local("test@test.com", "test")

    assert res is None


def test_non_existing_user():
    repo = MagicMock()
    repo.get_user_by_email.return_value = None

    service = AuthService(repo)
    res = service.authenticate_local("test.test@test.com", "test")
    assert res is None
