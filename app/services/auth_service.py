from flask import url_for

from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService


class AuthService:
    def __init__(self, user_repo: UserRepoProtocol):
        self.repo = user_repo

    def authenticate_local(self, email: str, password: str) -> str | None:
        user = self.repo.get_user_by_email(email)
        if not user or user.oauth != "local":
            return None
        if PasswordService.verify_password(password, user.hashed_password):
            return PasswordService.generate_token(user.id)
        return None
