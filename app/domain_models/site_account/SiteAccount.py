from dataclasses import dataclass

from flask import json


@dataclass
class SiteAccount:
    id: int
    name: str
    creator_id: int
    layout: str

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'creator_id': self.creator_id,
            'layout': json.loads(self.layout)
        }