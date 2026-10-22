from dataclasses import dataclass, field

from flask import json


@dataclass
class SiteAccount:
    id: int
    name: str
    creator_id: int
    layout: str
    profile_picture: str | None = None
    banner: str = ""
    colors: list[str] = field(default_factory=list)
    contact: list[dict[str, str]] = field(default_factory=list)
    description: str = ""
    visible: bool = True

    @property
    def picture(self) -> str:
        return self.profile_picture or ""

    @picture.setter
    def picture(self, value: str):
        self.profile_picture = value or None

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'layout': json.loads(self.layout),
            'picture': self.picture,
            'banner': self.banner,
            'colors': self.colors,
            'contact': self.contact,
            'description': self.description,
            'visible': self.visible,
        }
