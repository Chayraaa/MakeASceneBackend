from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class Message:
    user_id: int
    title: str
    message: str
    id: int = -1
    sent_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    read: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "sent_at": self.sent_at.isoformat(),
            "read": self.read,
        }
