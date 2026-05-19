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
    user.email = "test@test.com"

    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)

    with patch(
        "app.services.google_oauth_service.PasswordService.generate_exchange_token",
        return_value="exchange_token"
    ) as mock_exchange:
        res = service.authenticate_user(token)

    mock_exchange.assert_called_once_with("test@test.com")

    user_repo.update_user.assert_called_once_with(user)

    refresh_repo.create.assert_not_called()

    assert res == "exchange_token"


def test_non_existing_user():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "google"
    user.email = "test@test.com"

    user_repo.get_user_by_email.side_effect = [None, user]

    service = GoogleOauthService(user_repo, refresh_repo)

    with patch(
        "app.services.google_oauth_service.PasswordService.generate_exchange_token",
        return_value="exchange_token"
    ) as mock_exchange:
        res = service.authenticate_user(token)

    user_repo.create_user.assert_called_once_with(
        email="test@test.com",
        password="",
        oauth="google"
    )

    user_repo.update_user.assert_called_once_with(user)

    mock_exchange.assert_called_once_with("test@test.com")

    refresh_repo.create.assert_not_called()

    assert res == "exchange_token"


def test_wrong_oauth_method():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    token = {"email": "test@test.com"}

    user = MagicMock()
    user.oauth = "local"

    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)

    res = service.authenticate_user(token)

    refresh_repo.create.assert_not_called()

    user_repo.update_user.assert_not_called()

    assert res is None


def test_wrong_token_format():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    token = {"whatever": "test@test.com"}

    service = GoogleOauthService(user_repo, refresh_repo)

    res = service.authenticate_user(token)

    user_repo.get_user_by_email.assert_not_called()

    refresh_repo.create.assert_not_called()

    assert res is None


def test_exchange_valid_token():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    user = MagicMock()
    user.id = 123

    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)

    with (
        patch(
            "app.services.google_oauth_service.PasswordService.verify_exchange_token",
            return_value="test@test.com"
        ),
        patch(
            "app.services.google_oauth_service.PasswordService.generate_access_token",
            return_value="access"
        ),
        patch(
            "app.services.google_oauth_service.PasswordService.generate_refresh_token",
            return_value="refresh"
        ),
        patch(
            "app.services.google_oauth_service.PasswordService.hash_refresh_token",
            return_value="hashed_refresh"
        ) as mock_hash
    ):
        result = service.exchange("exchange_token")

    user_repo.get_user_by_email.assert_called_once_with("test@test.com")

    mock_hash.assert_called_once_with("refresh")

    refresh_repo.create.assert_called_once_with(
        hashed_token="hashed_refresh",
        user=user
    )

    assert result == ("access", "refresh")


def test_exchange_invalid_token():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    service = GoogleOauthService(user_repo, refresh_repo)

    with patch(
        "app.services.google_oauth_service.PasswordService.verify_exchange_token",
        return_value=None
    ):
        result = service.exchange("invalid")

    user_repo.get_user_by_email.assert_not_called()
    refresh_repo.create.assert_not_called()

    assert result is None


def test_exchange_user_not_found():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    user_repo.get_user_by_email.return_value = None

    service = GoogleOauthService(user_repo, refresh_repo)

    with patch(
        "app.services.google_oauth_service.PasswordService.verify_exchange_token",
        return_value="test@test.com"
    ):
        result = service.exchange("exchange_token")

    refresh_repo.create.assert_not_called()

    assert result is None


def test_exchange_refresh_token_generation_failed():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    user = MagicMock()
    user.id = 123

    user_repo.get_user_by_email.return_value = user

    service = GoogleOauthService(user_repo, refresh_repo)

    with (
        patch(
            "app.services.google_oauth_service.PasswordService.verify_exchange_token",
            return_value="test@test.com"
        ),
        patch(
            "app.services.google_oauth_service.PasswordService.generate_access_token",
            return_value="access"
        ),
        patch(
            "app.services.google_oauth_service.PasswordService.generate_refresh_token",
            return_value=None
        )
    ):
        result = service.exchange("exchange_token")

    refresh_repo.create.assert_not_called()

    assert result is None