from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

class Role(Enum):
    USER = 0
    MODERATOR = 1
    ADMIN = 2

@dataclass
class User:
    id: int
    hashed_password: str
    created_at: datetime
    oauth: str = "local"
    email: str = ""
    confirmed: bool = False
    mature: bool = True
    email_preference: bool = True
    role: int = Role.USER

