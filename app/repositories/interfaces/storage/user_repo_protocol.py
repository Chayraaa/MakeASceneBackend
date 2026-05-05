from typing import Protocol

from app.domain_models.user import User

# This is basically an interface in python (called Protocol)
# Every protocol should cover a single responsibility. Like user management in this case.
# For cards e.g., you would write a new protocol managing these and for relations between the user and the cards, too.
class UserRepoProtocol(Protocol):

    def get_user(self, user_id: int) -> User | None: ...

    def get_user_by_email(self, email: str) -> User | None: ...

    def create_user(self, password: str, email: str, oauth="local") -> bool: ...

    def update_user(self, user: User) -> bool: ...
