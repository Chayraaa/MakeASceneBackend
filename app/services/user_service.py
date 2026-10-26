from app.email_templates import render_email_template
from app.domain_models.user import User
from app.repositories.interfaces.external.email_protocol import EmailProtocol
from app.repositories.interfaces.storage.auth.confirm_token_repo_protocol import ConfirmTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService
from app.metrics import user_metrics, email_metrics
import os


# The user service is completely decoupled from the database. It just interacts with repo.
# repo is the protocol defined. It will accept any Object that provides the methods requested
# by the protocol. See SqlUserRepo for an example.
# Services are use-case-specific. So they handle a single use-case. In this case, user management.
# For cards, you would have a service that manages cards but also registers them to the user e.g.

def _assemble_mail(token: str):
    # This should point to the frontend.
    confirm_url = "/v1/auth/email/confirm?token="
    base_url = os.environ.get("BASE_URL", "http://127.0.0.1:5000")
    confirm_mail_text = render_email_template(
        "account_confirmation.html", url=f"{base_url}{confirm_url}{token}"
    )
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
            user_metrics.user_registered.labels(success='false').inc()
            return False

        token = PasswordService.generate_confirm_token()
        hashed_token = PasswordService.hash_confirm_token(token)

        self.user_repo.create_user(email=email, password=hashed_password)
        user = self.user_repo.get_user_by_email(email)
        if not user:
            user_metrics.user_registered.labels(success='false').inc()
            return False

        self.confirm_repo.create(hashed_token=hashed_token, user=user)
        email_text = _assemble_mail(token)
        with email_metrics.email_send_duration.labels(type='confirm').time():
            self.email_repo_protocol.send_email(
                subject="Willkommen bei Make A Scene! Bestätige deine E-Mail-Adresse, um loszulegen.",
                recipient=email,
                body=email_text,
            )
        email_metrics.email_sent.labels(type='confirm').inc()
        user_metrics.user_registered.labels(success='true').inc()
        return True

    def resend_confirmation_email(self, email: str) -> bool:
        user = self.get_user_by_email(email)
        if not user or user.confirmed:
            return False
        token = PasswordService.generate_confirm_token()
        hashed_token = PasswordService.hash_confirm_token(token)
        self.confirm_repo.create(hashed_token=hashed_token, user=user)
        email_text = _assemble_mail(token)
        with email_metrics.email_send_duration.labels(type='confirm').time():
            self.email_repo_protocol.send_email(
                subject="Willkommen bei Make A Scene! Bestätige deine E-Mail-Adresse, um loszulegen.",
                recipient=email,
                body=email_text,
            )
        email_metrics.email_sent.labels(type='confirm').inc()
        user_metrics.user_confirmation_email_resent.inc()
        return True

    def update_user(self, user: User) -> bool:
        return self.user_repo.update_user(user)

    def delete_user(self, user: User) -> bool:
        result = self.user_repo.delete_user(user)
        if result:
            user_metrics.user_deleted.inc()
        return result
