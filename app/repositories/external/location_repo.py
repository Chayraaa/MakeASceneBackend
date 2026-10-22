import os

import requests

from app.metrics.operation_metrics import duration, operations
from app.repositories.interfaces.external.location_protocol import LocationProtocol


class LocationRepo(LocationProtocol):
    def __init__(self):
        self.api_key = os.environ.get("GEOAPIFY_KEY")

    def _get(self, operation, path, params):
        with duration.labels("geoapify", operation).time():
            try:
                response = requests.get(
                    f"https://api.geoapify.com/{path}",
                    params={**params, "apiKey": self.api_key}, timeout=15,
                )
                if response.status_code != 200:
                    operations.labels("geoapify", operation, "error").inc()
                    return {}
                value = response.json()
            except Exception:
                operations.labels("geoapify", operation, "error").inc()
                raise
            operations.labels("geoapify", operation, "success").inc()
            return value

    def get_location_details(self, place_id: str) -> dict:
        return self._get("details", "v2/place-details", {
            "id": place_id, "features": "details,details.names",
        })

    def autocomplete_location(self, query: str) -> list[dict]:
        return self._get("autocomplete", "v1/geocode/autocomplete", {
            "text": query, "limit": 5, "lang": "de", "format": "json",
        }).get("results", [])
