from dataclasses import dataclass
from datetime import datetime


@dataclass
class Message:
    id: int
    user_id: int
    message: str
    sent_at: datetime
    read: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "message": self.message,
            "sent_at": self.sent_at.isoformat(),
            "read": self.read,
        }
