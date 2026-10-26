from dataclasses import dataclass


@dataclass
class SiteAccountSubscription:
    user_id: int
    site_account_id: int
    id: int = -1
    notifications_enabled: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "site_account_id": self.site_account_id,
            "notifications_enabled": self.notifications_enabled,
        }
