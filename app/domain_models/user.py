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
    role: int = Role.USER.value
    timezone: str = "UTC"

    def to_dict(self):
        return {
            "id": self.id,
            "email": self.email,
            "mature": self.mature,
            "email_preference": self.email_preference,
            "timezone": self.timezone,
            "role": self.role.value if isinstance(self.role, Role) else self.role,
        }

