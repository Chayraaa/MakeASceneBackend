from unittest.mock import MagicMock, patch

from app.services.user_service import UserService


def test_get_user():
    repo = MagicMock()

    service = UserService(repo)
    service.get_user(1)

    repo.get_user.assert_called_once_with(1)

def test_get_user_by_email():
    repo = MagicMock()

    service = UserService(repo)
    service.get_user_by_email("test@test.com")

    repo.get_user_by_email.assert_called_once_with("test@test.com")

def test_create_user():
    repo = MagicMock()
    service = UserService(repo)

    with patch("app.services.user_service.PasswordService.hash_password", return_value="hashed"):
        service.create_user("test@test.com", "pw")

    repo.create_user.assert_called_once_with(
        email="test@test.com",
        password="hashed",
    )

def test_update_user():
    repo = MagicMock()
    service = UserService(repo)

    user = MagicMock()

    service.update_user(user)

    repo.update_user.assert_called_once_with(user)