from typing import Protocol

from app.domain_models.auth.confirm_token import ConfirmToken
from app.domain_models.user import User


class ConfirmTokenRepoProtocol(Protocol):
    def __init__(self, session): ...

    def create(self, hashed_token: str, user: User) -> bool: ...

    def get_by_token_hash(self, hashed_token: str) -> ConfirmToken | None: ...

    def revoke(self, confirm_token: ConfirmToken) -> bool: ...
