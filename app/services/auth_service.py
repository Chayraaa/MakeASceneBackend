from datetime import datetime, timezone

from app.domain_models.user import User
from app.repositories.interfaces.storage.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.refresh_token_repo_protocol import RefreshTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService


class AuthService:
    def __init__(self, user_repo: UserRepoProtocol, refresh_token_repo: RefreshTokenRepoProtocol,
                 confirm_token_repo: ConfirmTokenRepoProtocol):
        self.repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.confirm_token_repo = confirm_token_repo

    def authenticate_local(self, email: str, password: str) -> tuple[str, str] | None:
        user = self.repo.get_user_by_email(email)
        if not user or user.oauth != "local":
            return None
        if not PasswordService.verify_password(password, user.hashed_password):
            return None

        access_token = PasswordService.generate_access_token(user.id)
        refresh_token = PasswordService.generate_refresh_token()
        if refresh_token is None:
            return None
        refresh_token_hash = PasswordService.hash_refresh_token(refresh_token)
        if refresh_token_hash is None:
            return None

        self.refresh_token_repo.create(hashed_token=refresh_token_hash, user=user)
        return access_token, refresh_token

    def refresh_session(self, refresh_token: str) -> tuple[str, str] | None:
        refresh_token_hash = PasswordService.hash_refresh_token(refresh_token)
        session = self.refresh_token_repo.get_by_token_hash(refresh_token_hash)
        if not session:
            return None
        if session.revoked:
            return None
        if session.expires_at < datetime.now(timezone.utc):
            return None
        access_token = PasswordService.generate_access_token(session.user_id)
        new_refresh_token = PasswordService.generate_refresh_token()
        if new_refresh_token is None:
            return None
        new_refresh_token_hash = PasswordService.hash_refresh_token(new_refresh_token)
        if new_refresh_token_hash is None:
            return None

        self.refresh_token_repo.revoke(session)
        self.refresh_token_repo.create(
            user=User(id=session.user_id, hashed_password="", oauth="", email=""),
            hashed_token=new_refresh_token_hash,
        )

        return access_token, new_refresh_token

    def confirm_email(self, token: str) -> bool:
        token_hash = PasswordService.hash_confirm_token(token)
        found_token = self.confirm_token_repo.get_by_token_hash(token_hash)
        if not found_token:
            return False
        if found_token.revoked:
            return False
        if found_token.expires_at < datetime.now(timezone.utc):
            return False
        user = self.repo.get_user(found_token.user_id)
        if not user:
            return False
        user.confirmed = True
        self.repo.update_user(user)
        self.confirm_token_repo.revoke(found_token)
        return True
