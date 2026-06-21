from dataclasses import dataclass


@dataclass
class SiteAccount:
    id: int
    name: str
    creator_id: int
    layout: str