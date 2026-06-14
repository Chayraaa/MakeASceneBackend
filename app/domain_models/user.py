from dataclasses import dataclass
from datetime import datetime, timezone


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
    role: str = "user"
