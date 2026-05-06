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
    token = PasswordService.generate_token(user_id=123)

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
