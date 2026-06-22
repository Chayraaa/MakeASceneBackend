from dataclasses import dataclass


@dataclass
class SiteAccountApplication:
    id: int
    requestor_id: int
    artist_name: str
    account_name: str
    reason: str
    sources: list[str]
    contacts: list[str]

    def to_dict(self):
        return {
            'id': self.id,
            'requestor_id': self.requestor_id,
            'artist_name': self.artist_name,
            'account_name': self.account_name,
            'reason': self.reason,
            'sources': self.sources,
            'contacts': self.contacts
        }