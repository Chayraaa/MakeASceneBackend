import requests

from app.repositories.interfaces.external.location_protocol import LocationProtocol
import os


class LocationRepo(LocationProtocol):
    def __init__(self):
        self.api_key = os.environ.get("GEOAPIFY_KEY")

    def get_location_details(self, place_id: str) -> dict:
        ...

    def autocomplete_location(self, query: str) -> list[dict]:
        url = f"https://api.geoapify.com/v1/geocode/autocomplete?text={query}&limit=5&lang=de&format=json&apiKey={self.api_key}"

        payload = {}
        headers = {}

        response = requests.request("GET", url, headers=headers, data=payload)

        return response.json()["results"]
