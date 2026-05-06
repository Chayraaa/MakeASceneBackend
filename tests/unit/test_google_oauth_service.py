from unittest.mock import MagicMock, patch

from app.services.google_oauth_service import GoogleOauthService


def test_valid_auth():
    repo = MagicMock()
    token = {
        "email": "test@test.com"
    }
    user = MagicMock()
    user.oauth = "google"
    user.id = 123
    repo.get_user_by_email.return_value = user

    service = GoogleOauthService(repo)
    with patch("app.services.google_oauth_service.PasswordService.generate_token", return_value="token"):
        jwt = service.authenticate_user(token)

    repo.update_user.assert_called_once_with(
        user
    )

    assert jwt == "token"


def test_non_existing_user():
    repo = MagicMock()
    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "google"
    user.id = 123

    repo.get_user_by_email.side_effect = [None, user]

    service = GoogleOauthService(repo)

    with patch("app.services.google_oauth_service.PasswordService.generate_token", return_value="token"):
        jwt = service.authenticate_user(token)

    repo.create_user.assert_called_once_with(
        email="test@test.com",
        password="",
        oauth="google"
    )

    repo.update_user.assert_called_once_with(user)

    assert jwt == "token"


def test_wrong_oauth_method():
    repo = MagicMock()
    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "local"
    user.id = 123

    repo.get_user_by_email.return_value = user

    service = GoogleOauthService(repo)
    jwt = service.authenticate_user(token)

    assert jwt is None


def test_wrong_token_format():
    repo = MagicMock()
    token = {"whatever": "test@test.com"}

    user = MagicMock()
    user.oauth = "google"
    user.id = 123

    service = GoogleOauthService(repo)
    jwt = service.authenticate_user(token)

    assert jwt is None
