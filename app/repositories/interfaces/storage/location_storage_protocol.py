from typing import Protocol

from app.domain_models.Location import Location


class LocationStorageProtocol(Protocol):
    def __init__(self, session):
        ...

    def add_location(self, location: Location) -> bool:
        ...

    def remove_location(self, location: Location) -> bool:
        ...

    def get_location_by_place_id(self, place_id: str) -> Location | None:
        ...

    def get_location(self, location_id: int) -> Location | None:
        ...

    def update_location(self, location: Location) -> bool:
        ...