from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch

from app.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_service(user_repo=None, refresh_repo=None, confirm_repo=None, email_repo=None, password_reset_repo=None):
    return AuthService(
        user_repo or MagicMock(),
        refresh_repo or MagicMock(),
        confirm_repo or MagicMock(),
        email_repo or MagicMock(),
        password_reset_repo or MagicMock()
    )


def _valid_session(*, revoked=False, expired=False, user_id=123):
    session = MagicMock()
    session.revoked = revoked
    session.user_id = user_id
    session.expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(days=1)
    )
    return session


def _valid_confirm_token(*, revoked=False, expired=False, user_id=42):
    token = MagicMock()
    token.revoked = revoked
    token.user_id = user_id
    token.expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(days=1)
    )
    return token


def test_valid_auth():
    user_repo = MagicMock()
    refresh_repo = MagicMock()

    user = MagicMock()
    user.oauth = "local"
    user.hashed_password = "hashed"
    user.id = 123
    user_repo.get_user_by_email.return_value = user

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.verify_password", return_value=True), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="refresh"), \
            patch("app.services.auth_service.PasswordService.hash_refresh_token",
                  return_value="hashed_refresh") as mock_hash:
        res = service.authenticate_local("test@test.com", "test")

    mock_hash.assert_called_once_with("refresh")
    refresh_repo.create.assert_called_once_with(hashed_token="hashed_refresh", user=user)
    assert res == ("token", "refresh")


def test_invalid_password():
    user_repo = MagicMock()
    user = MagicMock()
    user.oauth = "local"
    user_repo.get_user_by_email.return_value = user
    refresh_repo = MagicMock()

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)
    with patch("app.services.auth_service.PasswordService.verify_password", return_value=False):
        res = service.authenticate_local("test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_invalid_oauth():
    user_repo = MagicMock()
    user = MagicMock()
    user.oauth = "google"
    user_repo.get_user_by_email.return_value = user
    refresh_repo = MagicMock()

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)
    res = service.authenticate_local("test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_non_existing_user():
    user_repo = MagicMock()
    user_repo.get_user_by_email.return_value = None
    refresh_repo = MagicMock()

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)
    res = service.authenticate_local("test.test@test.com", "test")

    refresh_repo.create.assert_not_called()
    assert res is None


def test_authenticate_local_refresh_token_generation_fails():
    """generate_refresh_token() → None: kein Token wird gespeichert."""
    user_repo = MagicMock()
    user = MagicMock()
    user.oauth = "local"
    user.hashed_password = "hashed"
    user.id = 123  # fix: echte int-ID damit generate_access_token JSON-serialisierbar ist
    user_repo.get_user_by_email.return_value = user
    refresh_repo = MagicMock()

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.verify_password", return_value=True), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value=None):
        res = service.authenticate_local("test@test.com", "pw")

    assert res is None
    refresh_repo.create.assert_not_called()


def test_authenticate_local_refresh_token_hash_fails():
    """hash_refresh_token() → None: kein Token wird gespeichert."""
    user_repo = MagicMock()
    user = MagicMock()
    user.oauth = "local"
    user.hashed_password = "hashed"
    user.id = 123
    user_repo.get_user_by_email.return_value = user
    refresh_repo = MagicMock()

    service = _make_service(user_repo=user_repo, refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.verify_password", return_value=True), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value=None):
        res = service.authenticate_local("test@test.com", "pw")

    assert res is None
    refresh_repo.create.assert_not_called()


def test_refresh_session_valid():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = _valid_session()

    service = _make_service(refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="new_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_called_once()
    refresh_repo.create.assert_called_once()
    assert res == ("token", "new_refresh")


def test_refresh_session_revoked():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = _valid_session(revoked=True)

    service = _make_service(refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_expired():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = _valid_session(expired=True)

    service = _make_service(refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_not_found():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = None

    service = _make_service(refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="hashed_refresh"):
        res = service.refresh_session("refresh")

    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()
    assert res is None


def test_refresh_session_new_token_generation_fails():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = _valid_session()

    service = _make_service(refresh_repo=refresh_repo)

    with patch("app.services.auth_service.PasswordService.hash_refresh_token", return_value="h"), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value=None):
        res = service.refresh_session("refresh")

    assert res is None
    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()


def test_refresh_session_new_token_hash_fails():
    refresh_repo = MagicMock()
    refresh_repo.get_by_token_hash.return_value = _valid_session()

    service = _make_service(refresh_repo=refresh_repo)

    # Erster Call (Lookup-Hash) → "h", zweiter Call (neuer Token-Hash) → None
    with patch("app.services.auth_service.PasswordService.hash_refresh_token", side_effect=["h", None]), \
            patch("app.services.auth_service.PasswordService.generate_access_token", return_value="token"), \
            patch("app.services.auth_service.PasswordService.generate_refresh_token", return_value="new"):
        res = service.refresh_session("refresh")

    assert res is None
    refresh_repo.revoke.assert_not_called()
    refresh_repo.create.assert_not_called()


# ---------------------------------------------------------------------------
# confirm_email
# ---------------------------------------------------------------------------

def test_confirm_email_token_not_found():
    confirm_repo = MagicMock()
    confirm_repo.get_by_token_hash.return_value = None

    service = _make_service(confirm_repo=confirm_repo)

    with patch("app.services.auth_service.PasswordService.hash_confirm_token", return_value="h"):
        result = service.confirm_email("plain-token")

    assert result is False
    confirm_repo.revoke.assert_not_called()


def test_confirm_email_token_revoked():
    confirm_repo = MagicMock()
    confirm_repo.get_by_token_hash.return_value = _valid_confirm_token(revoked=True)

    service = _make_service(confirm_repo=confirm_repo)

    with patch("app.services.auth_service.PasswordService.hash_confirm_token", return_value="h"):
        result = service.confirm_email("plain-token")

    assert result is False
    confirm_repo.revoke.assert_not_called()


def test_confirm_email_token_expired():
    confirm_repo = MagicMock()
    confirm_repo.get_by_token_hash.return_value = _valid_confirm_token(expired=True)

    service = _make_service(confirm_repo=confirm_repo)

    with patch("app.services.auth_service.PasswordService.hash_confirm_token", return_value="h"):
        result = service.confirm_email("plain-token")

    assert result is False
    confirm_repo.revoke.assert_not_called()


def test_confirm_email_user_not_found():
    user_repo = MagicMock()
    user_repo.get_user.return_value = None
    confirm_repo = MagicMock()
    confirm_repo.get_by_token_hash.return_value = _valid_confirm_token()

    service = _make_service(user_repo=user_repo, confirm_repo=confirm_repo)

    with patch("app.services.auth_service.PasswordService.hash_confirm_token", return_value="h"):
        result = service.confirm_email("plain-token")

    assert result is False
    user_repo.update_user.assert_not_called()
    confirm_repo.revoke.assert_not_called()


def test_confirm_email_valid():
    user = MagicMock()
    user_repo = MagicMock()
    user_repo.get_user.return_value = user

    found_token = _valid_confirm_token(user_id=42)
    confirm_repo = MagicMock()
    confirm_repo.get_by_token_hash.return_value = found_token

    service = _make_service(user_repo=user_repo, confirm_repo=confirm_repo)

    with patch("app.services.auth_service.PasswordService.hash_confirm_token", return_value="h"):
        result = service.confirm_email("plain-token")

    assert result is True
    assert user.confirmed is True
    user_repo.update_user.assert_called_once_with(user)
    confirm_repo.revoke.assert_called_once_with(found_token)


# ---------------------------------------------------------------------------
# password reset
# ---------------------------------------------------------------------------

def _valid_reset_token(*, revoked=False, expired=False, user_id=42):
    token = MagicMock()
    token.revoked = revoked
    token.user_id = user_id
    token.expires_at = (
        datetime.now(timezone.utc) - timedelta(seconds=1)
        if expired
        else datetime.now(timezone.utc) + timedelta(days=1)
    )
    return token


def test_request_password_reset_user_not_found():
    user_repo = MagicMock()
    user_repo.get_user_by_email.return_value = None

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = MagicMock()
    service.email_repo = MagicMock()

    res = service.request_password_reset("test@test.com")

    assert res is False
    service.password_reset_repo.create.assert_not_called()
    service.email_repo.send_email.assert_not_called()


def test_request_password_reset_success():
    user = MagicMock()
    user_repo = MagicMock()
    user_repo.get_user_by_email.return_value = user

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = MagicMock()
    service.email_repo = MagicMock()

    with patch("app.services.auth_service.PasswordService.generate_reset_token", return_value="plain-token"), \
            patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="hashed-token"), \
            patch("app.services.auth_service._assemble_password_reset_mail", return_value="mail-body"):
        res = service.request_password_reset("test@test.com")

    assert res is True
    service.password_reset_repo.create.assert_called_once_with(
        hashed_token="hashed-token",
        user=user
    )
    service.email_repo.send_email.assert_called_once()


# ---------------------------------------------------------------------------
# reset_password
# ---------------------------------------------------------------------------

def test_reset_password_token_not_found():
    user_repo = MagicMock()
    reset_repo = MagicMock()
    reset_repo.get_by_token_hash.return_value = None

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = reset_repo

    with patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="h"):
        res = service.reset_password("token", "new-pass")

    assert res is False


def test_reset_password_token_revoked():
    user_repo = MagicMock()
    reset_repo = MagicMock()
    reset_repo.get_by_token_hash.return_value = _valid_reset_token(revoked=True)

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = reset_repo

    with patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="h"):
        res = service.reset_password("token", "new-pass")

    assert res is False


def test_reset_password_token_expired():
    user_repo = MagicMock()
    reset_repo = MagicMock()
    reset_repo.get_by_token_hash.return_value = _valid_reset_token(expired=True)

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = reset_repo

    with patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="h"):
        res = service.reset_password("token", "new-pass")

    assert res is False


def test_reset_password_user_not_found():
    user_repo = MagicMock()
    user_repo.get_user.return_value = None

    reset_token = _valid_reset_token()
    reset_repo = MagicMock()
    reset_repo.get_by_token_hash.return_value = reset_token

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = reset_repo

    with patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="h"):
        res = service.reset_password("token", "new-pass")

    assert res is False
    reset_repo.revoke.assert_not_called()


def test_reset_password_success():
    user = MagicMock()

    user_repo = MagicMock()
    user_repo.get_user.return_value = user

    reset_token = _valid_reset_token()
    reset_repo = MagicMock()
    reset_repo.get_by_token_hash.return_value = reset_token

    service = _make_service(user_repo=user_repo)
    service.password_reset_repo = reset_repo

    with patch("app.services.auth_service.PasswordService.hash_reset_token", return_value="hashed"), \
            patch("app.services.auth_service.PasswordService.hash_password", return_value="new-hash"):
        res = service.reset_password("token", "new-pass")

    assert res is True
    assert user.hashed_password == "new-hash"
    user_repo.update_user.assert_called_once_with(user)
    reset_repo.revoke.assert_called_once_with(reset_token)


# ---------------------------------------------------------------------------
# logout
# ---------------------------------------------------------------------------

def test_logout_multiple_tokens():
    user = MagicMock()

    token1 = MagicMock()
    token2 = MagicMock()

    refresh_repo = MagicMock()
    refresh_repo.get_by_user.return_value = [token1, token2]

    service = _make_service(refresh_repo=refresh_repo)

    res = service.logout(user)

    assert res is True
    refresh_repo.revoke.assert_any_call(token1)
    refresh_repo.revoke.assert_any_call(token2)


def test_logout_no_tokens():
    user = MagicMock()

    refresh_repo = MagicMock()
    refresh_repo.get_by_user.return_value = []

    service = _make_service(refresh_repo=refresh_repo)

    res = service.logout(user)

    assert res is True
    refresh_repo.revoke.assert_not_called()
