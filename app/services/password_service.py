from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
import jwt
import datetime
import os


ph = PasswordHasher()

jwt_secret_key = os.environ.get("JWT_SECRET")
if not jwt_secret_key:
    raise ValueError("JWT_SECRET environment variable is not set")


class PasswordService:

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
    def generate_token(user_id: int):
        payload = {
            "id": user_id,
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
            return payload.get("id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None