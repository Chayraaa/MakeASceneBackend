from dataclasses import dataclass

from geoalchemy2 import Geometry


@dataclass
class Location:
    id: int
    place_id: str
    details: str
    geometry: Geometry
