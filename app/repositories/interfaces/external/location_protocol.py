from typing import Protocol


class LocationProtocol(Protocol):
    def __init__(self):
        ...

    def get_location_details(self, place_id: str) -> dict:
        ...

    def autocomplete_location(self, query: str) -> list[dict]:
        ...