from datetime import datetime, timezone, timedelta

import jwt

from app.services.password_service import PasswordService


def test_hash_and_verify_password():
    password = "mysecret"

    hashed = PasswordService.hash_password(password)

    assert hashed != password
    assert PasswordService.verify_password(password, hashed)


def test_verify_wrong_password():
    hashed = PasswordService.hash_password("correct")

    assert not PasswordService.verify_password("wrong", hashed)


def test_generate_and_verify_token():
    token = PasswordService.generate_access_token(user_id=123)

    user_id = PasswordService.verify_token(token)

    assert user_id == 123


def test_verify_invalid_token():
    result = PasswordService.verify_token("invalid.token.here")

    assert result is None


def test_expired_token():
    expired_payload = {
        "id": 123,
        "exp": (datetime.now(timezone.utc) - timedelta(seconds=1)).timestamp(),
    }

    token = jwt.encode(expired_payload, PasswordService.get_secret(), algorithm="HS256")

    result = PasswordService.verify_token(token)

    assert result is None

def test_generate_refresh_token():
    token = PasswordService.generate_refresh_token()

    assert token is not None
    assert len(token) > 0


def test_refresh_tokens_are_unique():
    token1 = PasswordService.generate_refresh_token()
    token2 = PasswordService.generate_refresh_token()

    assert token1 != token2


def test_hash_refresh_token():
    token = PasswordService.generate_refresh_token()

    hashed = PasswordService.hash_refresh_token(token)

    assert hashed != token
    assert len(hashed) == 64


def test_hash_refresh_token_is_deterministic():
    token = PasswordService.generate_refresh_token()

    assert PasswordService.hash_refresh_token(token) == PasswordService.hash_refresh_token(token)


def test_hash_refresh_token_different_tokens():
    token1 = PasswordService.generate_refresh_token()
    token2 = PasswordService.generate_refresh_token()

    assert PasswordService.hash_refresh_token(token1) != PasswordService.hash_refresh_token(token2)

def test_generate_and_verify_exchange_token():
    token = PasswordService.generate_exchange_token("test@test.com")

    email = PasswordService.verify_exchange_token(token)

    assert email == "test@test.com"


def test_verify_exchange_token_wrong_type():
    payload = {
        "email": "test@test.com",
        "type": "access",
        "exp": (
            datetime.now(timezone.utc) + timedelta(minutes=1)
        ).timestamp()
    }

    token = jwt.encode(
        payload,
        PasswordService.get_secret(),
        algorithm="HS256"
    )

    result = PasswordService.verify_exchange_token(token)

    assert result is None


def test_verify_exchange_token_invalid():
    result = PasswordService.verify_exchange_token("invalid.token")

    assert result is None


def test_verify_exchange_token_expired():
    payload = {
        "email": "test@test.com",
        "type": "exchange",
        "exp": (
            datetime.now(timezone.utc) - timedelta(seconds=1)
        ).timestamp()
    }

    token = jwt.encode(
        payload,
        PasswordService.get_secret(),
        algorithm="HS256"
    )

    result = PasswordService.verify_exchange_token(token)

    assert result is None