from dataclasses import dataclass


@dataclass
class EventSubscription:
    user_id: int
    event_id: int
    id: int = -1
    notifications_enabled: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_id": self.event_id,
            "notifications_enabled": self.notifications_enabled,
        }
