from datetime import datetime, timezone

from app.domain_models.user import User
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.storage.auth.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.auth.password_reset_token_repo_protocol import PasswordResetTokenRepoProtocol
from app.repositories.interfaces.storage.auth.refresh_token_repo_protocol import RefreshTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService
import os


def _assemble_password_reset_mail(token: str):
    # This should point to the frontend.
    reset_url = "/v1/auth/password/reset?token="
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000")

    reset_mail_text = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Reset your password</title>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f4f4; font-family: Arial, sans-serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="padding: 40px 0;">
        <tr>
          <td align="center">
            <table
              width="600"
              cellpadding="0"
              cellspacing="0"
              style="
                background-color: #ffffff;
                border-radius: 12px;
                padding: 40px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.05);
              "
            >
              <tr>
                <td align="center">
                  <h1 style="margin: 0; color: #222222; font-size: 28px;">
                    Reset your password
                  </h1>

                  <p style="margin-top: 20px; color: #555555; font-size: 16px; line-height: 1.6;">
                    We received a request to reset your password.  
                    Click the button below to choose a new one.
                  </p>

                  <a
                    href="{base_url}{reset_url}{token}"
                    style="
                      display: inline-block;
                      margin-top: 30px;
                      padding: 14px 28px;
                      background-color: #111827;
                      color: #ffffff;
                      text-decoration: none;
                      border-radius: 8px;
                      font-size: 16px;
                      font-weight: bold;
                    "
                  >
                    Reset Password
                  </a>

                  <p style="margin-top: 40px; color: #888888; font-size: 14px; line-height: 1.5;">
                    If you didn’t request a password reset, you can safely ignore this email.
                  </p>
                </td>
              </tr>
            </table>

            <p style="margin-top: 20px; color: #999999; font-size: 12px;">
              © 2026 Make A Scene
            </p>
          </td>
        </tr>
      </table>
    </body>
    </html>
    """

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
            user=User(id=session.user_id, hashed_password="", oauth="", email="", created_at=datetime.now(timezone.utc)),
            hashed_token=new_refresh_token_hash,
        )

        return access_token, new_refresh_token

    def logout(self, user: User) -> bool:
        refresh_tokens = self.refresh_token_repo.get_by_user(user)
        for refresh_token in refresh_tokens:
            self.refresh_token_repo.revoke(refresh_token)
        return True

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

    def request_password_reset(self, email: str) -> bool:
        token = PasswordService.generate_reset_token()
        hashed_token = PasswordService.hash_reset_token(token)
        user = self.repo.get_user_by_email(email)
        if not user:
            return False

        self.password_reset_repo.create(hashed_token=hashed_token, user=user)
        self.email_repo.send_email(subject="Reset your password", body=_assemble_password_reset_mail(token),
                                   recipient=email)
        return True

    def reset_password(self, token: str, new_password: str) -> bool:
        token_hash = PasswordService.hash_reset_token(token)
        found_token = self.password_reset_repo.get_by_token_hash(token_hash)
        if not found_token:
            return False
        if found_token.revoked:
            return False
        if found_token.expires_at < datetime.now(timezone.utc):
            return False
        user = self.repo.get_user(found_token.user_id)
        if not user:
            return False
        user.hashed_password = PasswordService.hash_password(new_password)
        self.repo.update_user(user)
        self.password_reset_repo.revoke(found_token)
        return True


