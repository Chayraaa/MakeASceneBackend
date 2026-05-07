from app.repositories.interfaces.storage.refresh_token_repo_protocol import RefreshTokenRepoProtocol
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService


class GoogleOauthService:
    def __init__(self, user_repo: UserRepoProtocol, refresh_repo: RefreshTokenRepoProtocol):
        self.user_repo = user_repo
        self.refresh_repo = refresh_repo

    def authenticate_user(self, token: dict) -> tuple[str, str] | None:
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

        jwt = PasswordService.generate_access_token(user.id)
        refresh_token = PasswordService.generate_refresh_token()
        if refresh_token is None:
            return None
        refresh_token_hash = PasswordService.hash_refresh_token(refresh_token)
        self.refresh_repo.create(hashed_token=refresh_token_hash, user=user)
        return jwt, refresh_token
