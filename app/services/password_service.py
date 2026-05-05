import datetime
import os

import jwt
from passlib.context import CryptContext

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
jwt_secret_key = os.environ.get("JWT_SECRET")
if not jwt_secret_key:
    raise ValueError("JWT_SECRET environment variable is not set")

class PasswordService:

    @staticmethod
    def hash_password(password: str) -> str:
        return password_context.hash(password)

    @staticmethod
    def verify_password(password: str, hashed_password: str) -> bool:
        return password_context.verify(password, hashed_password)

    # Generate a JWT token for the user
    @staticmethod
    def generate_token(user_id: int):
        payload = {
            "id": user_id,
            "exp": (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).timestamp(),
        }

        return jwt.encode(payload, jwt_secret_key, algorithm="HS256")

    # Checks the provided token and returns the user id if valid
    @staticmethod
    def verify_token(token: str):
        try:
            payload = jwt.decode(token, jwt_secret_key, algorithms=["HS256"])
            return payload.get("id")
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None