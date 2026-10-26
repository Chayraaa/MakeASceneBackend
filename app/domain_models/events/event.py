from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Event:
    name: str
    description: str
    from_: datetime
    till: datetime
    tags: list[int]
    place_id: str
    layout: int
    data: list[Any]
    owner_id: int
    access: list[str]
    detail_data: list[Any]
    repeating: str | None = None
    collaborators: list[int] = field(default_factory=list)
    id: int | None = None
    visible: bool = True

    def to_dict(self):
        return {
            "id": self.id,
            "visible": self.visible,
            "name": self.name,
            "description": self.description,
            "from": self.from_.isoformat(),
            "till": self.till.isoformat(),
            "tags": self.tags,
            "place-id": self.place_id,
            "layout": self.layout,
            "data": self.data,
            "owner-id": self.owner_id,
            "access": self.access,
            "detail-data": self.detail_data,
            "repeating": self.repeating,
            "collaborators": self.collaborators,
        }
