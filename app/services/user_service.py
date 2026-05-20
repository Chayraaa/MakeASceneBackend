from app.domain_models.user import User
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.storage.auth.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService
import os


# The user service is completely decoupled from the database. It just interacts with repo.
# repo is the protocol defined. It will accept any Object that provides the methods requested
# by the protocol. See SqlUserRepo for an example.
# Services are use-case-specific. So they handle a single use-case. In this case, user management.
# For cards, you would have a service that manages cards but also registers them to the user e.g.

def _assemble_mail(token: str):
    # This should point to the frontend.
    confirm_url = "/v1/auth/confirm-email?token="
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
    confirm_mail_text = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      <title>Confirm your email</title>
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
                    Confirm your email
                  </h1>

                  <p style="margin-top: 20px; color: #555555; font-size: 16px; line-height: 1.6;">
                    Thanks for signing up!  
                    Please confirm your email address by clicking the button below.
                  </p>

                  <a
                    href="{base_url}{confirm_url}{token}"
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
                    Confirm Email
                  </a>

                  <p style="margin-top: 40px; color: #888888; font-size: 14px; line-height: 1.5;">
                    If you didn’t create an account, you can safely ignore this email.
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
    return confirm_mail_text


class UserService:
    def __init__(self, user_repo: UserRepoProtocol, email_repo_protocol: EmailProtocol,
                 confirm_repo: ConfirmTokenRepoProtocol):
        self.user_repo = user_repo
        self.email_repo_protocol = email_repo_protocol
        self.confirm_repo = confirm_repo

    def get_user(self, user_id: int) -> User | None:
        return self.user_repo.get_user(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        return self.user_repo.get_user_by_email(email)

    def create_user(self, email: str, password: str) -> bool:
        hashed_password = PasswordService.hash_password(password)
        user = self.get_user_by_email(email)
        if user:
            return False

        token = PasswordService.generate_confirm_token()
        hashed_token = PasswordService.hash_confirm_token(token)

        self.user_repo.create_user(email=email, password=hashed_password)
        user = self.user_repo.get_user_by_email(email)
        if not user:
            return False

        self.confirm_repo.create(hashed_token=hashed_token, user=user)
        email_text = _assemble_mail(token)
        self.email_repo_protocol.send_email(
            subject="Welcome to Make A Scene! Confirm your email to get started.",
            recipient=email,
            body=email_text,
        )
        return True

    def resend_confirmation_email(self, email: str) -> bool:
        user = self.get_user_by_email(email)
        if not user or user.confirmed:
            return False
        token = PasswordService.generate_confirm_token()
        hashed_token = PasswordService.hash_confirm_token(token)
        self.confirm_repo.create(hashed_token=hashed_token, user=user)
        email_text = _assemble_mail(token)
        self.email_repo_protocol.send_email(
            subject="Welcome to Make A Scene! Confirm your email to get started.",
            recipient=email,
            body=email_text,
        )
        return True

    def update_user(self, user: User) -> bool:
        return self.user_repo.update_user(user)
