from cmath import exp

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
import hashlib
import datetime
import os
import secrets

ph = PasswordHasher()

jwt_secret_key = os.environ.get("JWT_SECRET")
if not jwt_secret_key:
    raise ValueError("JWT_SECRET environment variable is not set")


class PasswordService:

    @staticmethod
    def get_secret():
        return jwt_secret_key

    @staticmethod
    def hash_password(password: str) -> str:
        return ph.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        try:
            return ph.verify(hashed_password, password)
        except VerifyMismatchError:
            return False

    @staticmethod
    def generate_refresh_token():
        return secrets.token_urlsafe(64)

    @staticmethod
    def generate_confirm_token():
        return secrets.token_urlsafe(32)

    @staticmethod
    def hash_refresh_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def hash_confirm_token(token: str) -> str:
        return hashlib.sha256(token.encode()).hexdigest()

    @staticmethod
    def generate_access_token(user_id: int):
        payload = {
            "id": user_id,
            "type": "access",
            "exp": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(days=1)
            ).timestamp(),
        }

        return jwt.encode(payload, jwt_secret_key, algorithm="HS256")

    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
            if payload.get("type") != "access":
                return None
            return payload.get("id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None

    @staticmethod
    def generate_exchange_token(email: str):
        payload = {
            "email": email,
            "type": "exchange",
            "exp": (
                    datetime.datetime.now(datetime.timezone.utc)
                    + datetime.timedelta(minutes=1)
            ).timestamp()
        }
        return jwt.encode(payload, jwt_secret_key, algorithm="HS256")

    @staticmethod
    def verify_exchange_token(token: str):
        try:
            payload = jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
            if payload.get("type") != "exchange":
                return None
            return payload.get("email")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None
