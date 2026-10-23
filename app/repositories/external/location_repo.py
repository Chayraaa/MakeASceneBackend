import logging
import os

import requests

from app.metrics.operation_metrics import duration, operations
from app.repositories.interfaces.external.location_protocol import LocationProtocol


logger = logging.getLogger(__name__)


class LocationRepo(LocationProtocol):
    def __init__(self):
        self.api_key = os.environ.get("GEOAPIFY_KEY")

    def _get(self, operation, path, params):
        with duration.labels("geoapify", operation).time():
            if not self.api_key or not self.api_key.strip():
                operations.labels("geoapify", operation, "error").inc()
                logger.error("Geoapify %s failed: GEOAPIFY_KEY is missing or blank", operation)
                return {}
            try:
                response = requests.get(
                    f"https://api.geoapify.com/{path}",
                    params={**params, "apiKey": self.api_key}, timeout=15,
                )
                if response.status_code != 200:
                    operations.labels("geoapify", operation, "error").inc()
                    # URLs, response bodies and exception messages may contain the API key.
                    logger.error("Geoapify %s failed: HTTP %s", operation, response.status_code)
                    return {}
                value = response.json()
            except Exception as exc:
                operations.labels("geoapify", operation, "error").inc()
                logger.error("Geoapify %s failed: %s", operation, type(exc).__name__)
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
