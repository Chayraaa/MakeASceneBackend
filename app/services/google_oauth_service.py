from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService


class GoogleOauthService:
    def __init__(self, user_repo: UserRepoProtocol):
        self.user_repo = user_repo

    def authenticate_user(self, token: dict) -> str | None:
        email: str = token.get("email", "")
        if email == "":
            return None
        user = self.user_repo.get_user_by_email(email)
        if not user:
            self.user_repo.create_user(email=email, password="", oauth="google")
            user = self.user_repo.get_user_by_email(email)

        if user.oauth != "google":
            return None
        self.user_repo.update_user(user)

        jwt = PasswordService.generate_token(user.id)
        return jwt
