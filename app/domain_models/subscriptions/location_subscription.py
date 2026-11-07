from dataclasses import dataclass


@dataclass
class LocationSubscription:
    user_id: int
    location_id: int
    id: int = -1

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "location_id": self.location_id,
        }
