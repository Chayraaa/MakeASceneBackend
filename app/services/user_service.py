from app.domain_models.user import User
from app.repositories.interfaces.storage.user_repo_protocol import UserRepoProtocol
from app.services.password_service import PasswordService


# The user service is completely decoupled from the database. It just interacts with repo.
# repo is the protocol defined. It will accept any Object that provides the methods requested
# by the protocol. See SqlUserRepo for an example.
# Services are use-case-specific. So they handle a single use-case. In this case, user management.
# For cards, you would have a service that manages cards but also registers them to the user e.g.
class UserService:
    def __init__(self, repo: UserRepoProtocol):
        self.repo = repo

    def get_user(self, user_id: int) -> User | None:
        return self.repo.get_user(user_id)

    def get_user_by_email(self, email: str) -> User | None:
        return self.repo.get_user_by_email(email)

    def create_user(self, email: str, password: str) -> bool:
        hashed_password = PasswordService.hash_password(password)
        return self.repo.create_user(email=email, password=hashed_password)

    def update_user(self, user: User) -> bool:
        return self.repo.update_user(user)
