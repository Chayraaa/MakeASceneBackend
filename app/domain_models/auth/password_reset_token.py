from dataclasses import dataclass
from datetime import datetime


@dataclass
class PasswordResetToken:
    id: int
    user_id: int
    hashed_token: str
    created_at: datetime
    expires_at: datetime
    revoked: bool
