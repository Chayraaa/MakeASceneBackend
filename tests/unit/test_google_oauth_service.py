from unittest.mock import MagicMock, patch

from app.services.google_oauth_service import GoogleOauthService


def test_valid_auth():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    token = {
        "email": "test@test.com"
    }
    user = MagicMock()
    user.oauth = "google"
    user.id = 123
    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)
    with patch("app.services.google_oauth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.google_oauth_service.PasswordService.generate_refresh_token", return_value="refresh"), \
            patch("app.services.google_oauth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh") as mock_hash:
        res = service.authenticate_user(token)

    mock_hash.assert_called_once_with("refresh")
    refresh_repo.create.assert_called_once_with(hashed_token="hashed_refresh", user=user)
    user_repo.update_user.assert_called_once_with(user)
    assert res == ("token", "refresh")


def test_non_existing_user():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "google"
    user.id = 123

    user_repo.get_user_by_email.side_effect = [None, user]

    service = GoogleOauthService(user_repo, refresh_repo)

    with patch("app.services.google_oauth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.google_oauth_service.PasswordService.generate_refresh_token", return_value="refresh"), \
            patch("app.services.google_oauth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.authenticate_user(token)

    user_repo.create_user.assert_called_once_with(
        email="test@test.com",
        password="",
        oauth="google"
    )
    user_repo.update_user.assert_called_once_with(user)
    refresh_repo.create.assert_called_once_with(hashed_token="hashed_refresh", user=user)
    assert res == ("token", "refresh")


def test_wrong_oauth_method():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "local"
    user.id = 123

    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)
    res = service.authenticate_user(token)

    refresh_repo.create.assert_not_called()
    assert res is None


def test_wrong_token_format():
    user_repo = MagicMock()
    refresh_repo = MagicMock()
    token = {"whatever": "test@test.com"}

    user = MagicMock()
    user.oauth = "google"
    user.id = 123

    service = GoogleOauthService(user_repo, refresh_repo)
    res = service.authenticate_user(token)

    refresh_repo.create.assert_not_called()
    assert res is None
