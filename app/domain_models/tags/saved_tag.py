from dataclasses import dataclass


@dataclass
class SavedTag:
    id: int
    user_id: int
    tag_id: int
