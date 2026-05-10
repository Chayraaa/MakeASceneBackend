from unittest.mock import MagicMock, patch, call

from app.services.user_service import UserService

## TEST CASES CURTESY OF CLAUDE

def test_get_user():
    repo = MagicMock()
    service = UserService(repo, MagicMock(), MagicMock())
    service.get_user(1)
    repo.get_user.assert_called_once_with(1)


def test_get_user_by_email():
    repo = MagicMock()
    service = UserService(repo, MagicMock(), MagicMock())
    service.get_user_by_email("test@test.com")
    repo.get_user_by_email.assert_called_once_with("test@test.com")


def test_update_user():
    repo = MagicMock()
    service = UserService(repo, MagicMock(), MagicMock())
    user = MagicMock()
    service.update_user(user)
    repo.update_user.assert_called_once_with(user)

def test_create_user_calls_repo_with_hashed_password():
    repo = MagicMock()
    repo.get_user_by_email.side_effect = [None, MagicMock()]  # fix
    service = UserService(repo, MagicMock(), MagicMock())

    with patch("app.services.user_service.PasswordService.hash_password", return_value="hashed_pw"):
        service.create_user("test@test.com", "plaintext")

    repo.create_user.assert_called_once_with(email="test@test.com", password="hashed_pw")


def test_create_user_sends_confirmation_email():
    repo = MagicMock()
    repo.get_user_by_email.side_effect = [None, MagicMock()]  # 1. Duplikat-Check, 2. nach create
    email_repo = MagicMock()
    service = UserService(repo, email_repo, MagicMock())

    with patch("app.services.user_service.PasswordService.hash_password", return_value="h"):
        service.create_user("test@test.com", "pw")

    email_repo.send_email.assert_called_once()
    _, kwargs = email_repo.send_email.call_args
    assert kwargs["recipient"] == "test@test.com"
    assert "confirm" in kwargs["subject"].lower() or "welcome" in kwargs["subject"].lower()



def test_create_user_email_body_contains_plain_token():
    repo = MagicMock()
    repo.get_user_by_email.side_effect = [None, MagicMock()]  # fix
    email_repo = MagicMock()
    service = UserService(repo, email_repo, MagicMock())

    plain_token = "plain-secret-token"
    hashed_token = "hashed-secret-token"

    with (
        patch("app.services.user_service.PasswordService.hash_password", return_value="h"),
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value=plain_token),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value=hashed_token),
    ):
        service.create_user("test@test.com", "pw")

    _, kwargs = email_repo.send_email.call_args
    assert plain_token in kwargs["body"]
    assert hashed_token not in kwargs["body"]


def test_create_user_stores_hashed_token_in_confirm_repo():
    created_user = MagicMock()
    repo = MagicMock()
    # Erstes call (Duplikat-Check) → None, zweites call (nach create) → created_user
    repo.get_user_by_email.side_effect = [None, created_user]
    confirm_repo = MagicMock()
    service = UserService(repo, MagicMock(), confirm_repo)

    plain_token = "plain-token"
    hashed_token = "hashed-token"

    with (
        patch("app.services.user_service.PasswordService.hash_password", return_value="h"),
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value=plain_token),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value=hashed_token),
    ):
        service.create_user("test@test.com", "pw")

    confirm_repo.create.assert_called_once_with(hashed_token=hashed_token, user=created_user)


def test_create_user_returns_true_on_success():
    repo = MagicMock()
    repo.get_user_by_email.side_effect = [None, MagicMock()]  # fix
    service = UserService(repo, MagicMock(), MagicMock())

    with patch("app.services.user_service.PasswordService.hash_password", return_value="h"):
        result = service.create_user("test@test.com", "pw")

    assert result is True

def test_create_user_existing_email_returns_false():
    repo = MagicMock()
    repo.get_user_by_email.return_value = MagicMock()  # User existiert bereits
    email_repo = MagicMock()
    confirm_repo = MagicMock()
    service = UserService(repo, email_repo, confirm_repo)

    result = service.create_user(email="test@test.com", password="pw")

    assert result is False
    repo.create_user.assert_not_called()
    email_repo.send_email.assert_not_called()
    confirm_repo.create.assert_not_called()


def test_create_user_fails_if_user_not_found_after_create():
    repo = MagicMock()
    repo.get_user_by_email.side_effect = [None, None]
    email_repo = MagicMock()
    confirm_repo = MagicMock()
    service = UserService(repo, email_repo, confirm_repo)

    with patch("app.services.user_service.PasswordService.hash_password", return_value="h"):
        result = service.create_user("test@test.com", "pw")

    assert result is False
    email_repo.send_email.assert_not_called()
    confirm_repo.create.assert_not_called()

def test_resend_confirmation_email_returns_false_if_user_not_found():
    repo = MagicMock()
    repo.get_user_by_email.return_value = None
    email_repo = MagicMock()
    confirm_repo = MagicMock()
    service = UserService(repo, email_repo, confirm_repo)

    result = service.resend_confirmation_email("test@test.com")

    assert result is False
    email_repo.send_email.assert_not_called()
    confirm_repo.create.assert_not_called()


def test_resend_confirmation_email_returns_false_if_already_confirmed():
    repo = MagicMock()
    user = MagicMock()
    user.confirmed = True
    repo.get_user_by_email.return_value = user
    email_repo = MagicMock()
    confirm_repo = MagicMock()
    service = UserService(repo, email_repo, confirm_repo)

    result = service.resend_confirmation_email("test@test.com")

    assert result is False
    email_repo.send_email.assert_not_called()
    confirm_repo.create.assert_not_called()


def test_resend_confirmation_email_stores_hashed_token_in_confirm_repo():
    repo = MagicMock()
    user = MagicMock()
    user.confirmed = False
    repo.get_user_by_email.return_value = user
    confirm_repo = MagicMock()
    service = UserService(repo, MagicMock(), confirm_repo)

    plain_token = "plain-token"
    hashed_token = "hashed-token"

    with (
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value=plain_token),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value=hashed_token),
    ):
        service.resend_confirmation_email("test@test.com")

    confirm_repo.create.assert_called_once_with(hashed_token=hashed_token, user=user)


def test_resend_confirmation_email_sends_email_with_correct_recipient_and_subject():
    repo = MagicMock()
    user = MagicMock()
    user.confirmed = False
    repo.get_user_by_email.return_value = user
    email_repo = MagicMock()
    service = UserService(repo, email_repo, MagicMock())

    with (
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value="t"),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value="h"),
    ):
        service.resend_confirmation_email("test@test.com")

    email_repo.send_email.assert_called_once()
    _, kwargs = email_repo.send_email.call_args
    assert kwargs["recipient"] == "test@test.com"
    assert "confirm" in kwargs["subject"].lower() or "welcome" in kwargs["subject"].lower()


def test_resend_confirmation_email_body_contains_plain_token():
    repo = MagicMock()
    user = MagicMock()
    user.confirmed = False
    repo.get_user_by_email.return_value = user
    email_repo = MagicMock()
    service = UserService(repo, email_repo, MagicMock())

    plain_token = "plain-secret-token"
    hashed_token = "hashed-secret-token"

    with (
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value=plain_token),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value=hashed_token),
    ):
        service.resend_confirmation_email("test@test.com")

    _, kwargs = email_repo.send_email.call_args
    assert plain_token in kwargs["body"]
    assert hashed_token not in kwargs["body"]


def test_resend_confirmation_email_returns_true_on_success():
    repo = MagicMock()
    user = MagicMock()
    user.confirmed = False
    repo.get_user_by_email.return_value = user
    service = UserService(repo, MagicMock(), MagicMock())

    with (
        patch("app.services.user_service.PasswordService.generate_confirm_token", return_value="t"),
        patch("app.services.user_service.PasswordService.hash_confirm_token", return_value="h"),
    ):
        result = service.resend_confirmation_email("test@test.com")

    assert result is True