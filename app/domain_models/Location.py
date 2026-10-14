from dataclasses import dataclass

from geoalchemy2 import WKBElement


@dataclass
class Location:
    id: int
    place_id: str
    details: str
    geometry: WKBElement
