from app.email_templates import render_email_template
from datetime import datetime, timezone

from app.domain_models.user import User
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.storage.auth.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.auth.password_reset_token_repo_protocol import PasswordResetTokenRepoProtocol
from app.repositories.interfaces.storage.auth.refresh_token_repo_protocol import RefreshTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService
from app.metrics import auth_metrics, email_metrics
import os


def _assemble_password_reset_mail(token: str):
    # This should point to the frontend.
    reset_url = "/v1/auth/password/reset?token="
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

    reset_mail_text = render_email_template(
        "password_reset.html", url=f"{base_url}{reset_url}{token}"
    )

    return reset_mail_text


class AuthService:
    def __init__(self, user_repo: UserRepoProtocol, refresh_token_repo: RefreshTokenRepoProtocol,
                 confirm_token_repo: ConfirmTokenRepoProtocol, email_repo: EmailProtocol,
                 password_reset_repo: PasswordResetTokenRepoProtocol):
        self.repo = user_repo
        self.refresh_token_repo = refresh_token_repo
        self.confirm_token_repo = confirm_token_repo
        self.email_repo = email_repo
        self.password_reset_repo = password_reset_repo

    def authenticate_local(self, email: str, password: str) -> tuple[str, str] | None:
        user = self.repo.get_user_by_email(email)
        if not user or user.oauth != "local" or not user.confirmed:
            auth_metrics.auth_login_attempts.labels(method='local', success='false').inc()
            return None
        if not PasswordService.verify_password(password, user.hashed_password):
            auth_metrics.auth_login_attempts.labels(method='local', success='false').inc()
            return None

        access_token = PasswordService.generate_access_token(user.id)
        refresh_token = PasswordService.generate_refresh_token()
        if refresh_token is None:
            auth_metrics.auth_login_attempts.labels(method='local', success='false').inc()
            return None
        refresh_token_hash = PasswordService.hash_refresh_token(refresh_token)
        if refresh_token_hash is None:
            auth_metrics.auth_login_attempts.labels(method='local', success='false').inc()
            return None
        old_tokens = self.refresh_token_repo.get_by_user(user)
        for old_token in old_tokens:
            self.refresh_token_repo.revoke(old_token)
        self.refresh_token_repo.create(hashed_token=refresh_token_hash, user=user)
        auth_metrics.auth_login_attempts.labels(method='local', success='true').inc()
        return access_token, refresh_token

    def refresh_session(self, refresh_token: str) -> tuple[str, str] | None:
        refresh_token_hash = PasswordService.hash_refresh_token(refresh_token)
        session = self.refresh_token_repo.get_by_token_hash(refresh_token_hash)
        if not session:
            auth_metrics.auth_token_refresh.labels(result='not_found').inc()
            return None
        if session.revoked:
            auth_metrics.auth_token_refresh.labels(result='revoked').inc()
            return None
        if session.expires_at < datetime.now(timezone.utc):
            auth_metrics.auth_token_refresh.labels(result='expired').inc()
            return None
        access_token = PasswordService.generate_access_token(session.user_id)
        new_refresh_token = PasswordService.generate_refresh_token()
        if new_refresh_token is None:
            auth_metrics.auth_token_refresh.labels(result='not_found').inc()
            return None
        new_refresh_token_hash = PasswordService.hash_refresh_token(new_refresh_token)
        if new_refresh_token_hash is None:
            auth_metrics.auth_token_refresh.labels(result='not_found').inc()
            return None

        self.refresh_token_repo.revoke(session)
        self.refresh_token_repo.create(
            user=User(id=session.user_id, hashed_password="", oauth="", email="", created_at=datetime.now(timezone.utc)),
            hashed_token=new_refresh_token_hash,
        )

        auth_metrics.auth_token_refresh.labels(result='success').inc()
        return access_token, new_refresh_token

    def logout(self, user: User) -> bool:
        refresh_tokens = self.refresh_token_repo.get_by_user(user)
        for refresh_token in refresh_tokens:
            self.refresh_token_repo.revoke(refresh_token)
        auth_metrics.auth_logout.inc()
        return True

    def confirm_email(self, token: str) -> bool:
        token_hash = PasswordService.hash_confirm_token(token)
        found_token = self.confirm_token_repo.get_by_token_hash(token_hash)
        if not found_token:
            auth_metrics.auth_email_confirmation.labels(result='not_found').inc()
            return False
        if found_token.revoked:
            auth_metrics.auth_email_confirmation.labels(result='revoked').inc()
            return False
        if found_token.expires_at < datetime.now(timezone.utc):
            auth_metrics.auth_email_confirmation.labels(result='expired').inc()
            return False
        user = self.repo.get_user(found_token.user_id)
        if not user:
            auth_metrics.auth_email_confirmation.labels(result='not_found').inc()
            return False
        user.confirmed = True
        self.repo.update_user(user)
        self.confirm_token_repo.revoke(found_token)
        auth_metrics.auth_email_confirmation.labels(result='success').inc()
        return True

    def request_password_reset(self, email: str) -> bool:
        token = PasswordService.generate_reset_token()
        hashed_token = PasswordService.hash_reset_token(token)
        user = self.repo.get_user_by_email(email)
        if not user:
            return False

        self.password_reset_repo.create(hashed_token=hashed_token, user=user)
        with email_metrics.email_send_duration.labels(type='password_reset').time():
            self.email_repo.send_email(subject="Passwort zurücksetzen", body=_assemble_password_reset_mail(token),
                                       recipient=email)
        email_metrics.email_sent.labels(type='password_reset').inc()
        auth_metrics.auth_password_reset_requested.inc()
        return True

    def reset_password(self, token: str, new_password: str) -> bool:
        token_hash = PasswordService.hash_reset_token(token)
        found_token = self.password_reset_repo.get_by_token_hash(token_hash)
        if not found_token:
            auth_metrics.auth_password_reset_completed.labels(success='false').inc()
            return False
        if found_token.revoked:
            auth_metrics.auth_password_reset_completed.labels(success='false').inc()
            return False
        if found_token.expires_at < datetime.now(timezone.utc):
            auth_metrics.auth_password_reset_completed.labels(success='false').inc()
            return False
        user = self.repo.get_user(found_token.user_id)
        if not user:
            auth_metrics.auth_password_reset_completed.labels(success='false').inc()
            return False
        user.hashed_password = PasswordService.hash_password(new_password)
        self.repo.update_user(user)
        self.password_reset_repo.revoke(found_token)
        auth_metrics.auth_password_reset_completed.labels(success='true').inc()
        return True
