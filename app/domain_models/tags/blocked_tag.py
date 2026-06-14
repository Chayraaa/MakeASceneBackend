from dataclasses import dataclass


@dataclass
class BlockedTag:
    id: int
    user_id: int
    tag_id: int
