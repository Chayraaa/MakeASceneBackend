import threading

_lock = threading.Lock()
_initialized = False


class TypesenseLocationSearchRepo:
    def __init__(self, client):
        self.client = client

    def _ensure_ready(self):
        global _initialized

        if not _initialized:
            with _lock:
                if not _initialized:
                    self._ensure_collection()
                    _initialized = True

    def _ensure_collection(self):
        try:
            self.client.collections["locations"].retrieve()
            return
        except:
            pass

        self.client.collections.create({
            "name": "locations",
            "fields": [
                {"name": "name", "type": "string", "optional": True},
                {"name": "country", "type": "string", "facet": True, "optional": True},
                {"name": "country_code", "type": "string", "facet": True, "optional": True},
                {"name": "state", "type": "string", "facet": True, "optional": True},
                {"name": "state_code", "type": "string", "facet": True, "optional": True},
                {"name": "county", "type": "string", "optional": True},
                {"name": "county_code", "type": "string", "optional": True},
                {"name": "postcode", "type": "string", "optional": True},
                {"name": "city", "type": "string", "optional": True},
                {"name": "street", "type": "string", "optional": True},
                {"name": "housenumber", "type": "string", "optional": True},
                {"name": "lat", "type": "float", "optional": True},
                {"name": "lon", "type": "float", "optional": True},
                {"name": "formatted", "type": "string"},
                {"name": "importance", "type": "float", "optional": True}
            ]
        })

    def add_location(self, location: dict) -> dict:
        self._ensure_ready()

        doc = {
            "id": location["place_id"]
        }

        fields = [
            "name",
            "country",
            "country_code",
            "state",
            "state_code",
            "county",
            "county_code",
            "postcode",
            "city",
            "street",
            "housenumber",
            "lat",
            "lon",
            "formatted",
        ]

        for field in fields:
            value = location.get(field)

            if value is not None:
                doc[field] = value

        importance = location.get("rank", {}).get("importance")

        if importance is not None:
            doc["importance"] = importance

        self.client.collections["locations"].documents.upsert(doc)

        return doc

    def autocomplete_location(self, query: str) -> list[dict]:
        self._ensure_ready()
        search_parameters = {
            "q": query,
            "query_by": "name,city,state,county,country,postcode,street,formatted",
            "query_by_weights": "10,10,8,6,3,4,7,2",
            "per_page": 10,
        }

        results = self.client \
            .collections["locations"] \
            .documents \
            .search(search_parameters)

        return [
            hit["document"]
            for hit in results["hits"]
        ]
