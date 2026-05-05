from dataclasses import dataclass


@dataclass
class User:
    id: int
    hashed_password: str
    oauth: str = "local"
    email: str = ""
