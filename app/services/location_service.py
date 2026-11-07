import json
from app.domain_models.user import User
from app.domain_models.subscriptions.location_subscription import LocationSubscription
from app.repositories.interfaces.storage.subscriptions.location_subscription_repo_protocol import LocationSubscriptionRepoProtocol
from geoalchemy2.shape import from_shape
import math
from app.metrics.operation_metrics import monitored, location_sources

from app.repositories.interfaces.external.search_engine_location_protocol import SearchEngineLocationProtocol
from app.repositories.interfaces.external.location_protocol import LocationProtocol
from app.domain_models.Location import Location
from shapely.geometry import shape
from app.repositories.interfaces.storage.location_storage_protocol import LocationStorageProtocol


class LocationService:
    def __init__(self, location_search_repo: SearchEngineLocationProtocol, location_api_repo: LocationProtocol, location_storage: LocationStorageProtocol,
                 subscription_repo: LocationSubscriptionRepoProtocol | None = None):
        self.location_search_repo = location_search_repo
        self.location_api_repo = location_api_repo
        self.location_storage = location_storage
        self.subscription_repo = subscription_repo

    # Fetches the location details:
    # Prio 1: Location DB Table
    # Prio 2: Location API
    @monitored("location", "resolve")
    def get_location_data(self, place_id: str) -> Location | None:
        location = self.location_storage.get_location_by_place_id(place_id)
        if location is not None:
            location_sources.labels("database").inc()
            return location

        resp = self.location_api_repo.get_location_details(place_id)
        feature = next((item for item in resp.get("features", []) if item.get("geometry")), None)
        if feature is not None:
            location_sources.labels("details").inc()
            details = feature["properties"]
            geometry = feature["geometry"]
        else:
            # Some valid autocomplete IDs have no Place Details feature. The
            # exact cached autocomplete result still provides an address/point.
            cached = (
                self.location_search_repo.get_location_by_place_id(place_id)
                if self.location_search_repo is not None else None
            )
            if not isinstance(cached, dict):
                location_sources.labels("unresolved").inc()
                return None
            try:
                longitude, latitude = float(cached["lon"]), float(cached["lat"])
            except (KeyError, TypeError, ValueError):
                location_sources.labels("unresolved").inc()
                return None
            if not (math.isfinite(longitude) and math.isfinite(latitude)
                    and -180 <= longitude <= 180 and -90 <= latitude <= 90):
                location_sources.labels("unresolved").inc()
                return None
            location_sources.labels("autocomplete").inc()
            details = {key: value for key, value in cached.items() if key != "id"}
            details["place_id"] = place_id
            geometry = {"type": "Point", "coordinates": [longitude, latitude]}
        s = shape(geometry)
        geo_obj = from_shape(s, srid=4326)
        location = Location(id=-1, place_id=place_id, details=details, geometry=geo_obj)
        if not self.location_storage.add_location(location):
            return self.location_storage.get_location_by_place_id(place_id)
        return location


    @monitored("location", "autocomplete")
    def autocomplete_location(self, query: str, force_api: bool = False) -> list[dict]:
        if force_api:
            res = self.location_api_repo.autocomplete_location(query)
            ret_val = []
            for location in res:
                ret_val.append(self.location_search_repo.add_location(location))
            return ret_val
        else:
            res = self.location_search_repo.autocomplete_location(query)
            if len(res) == 0:
                res = self.location_api_repo.autocomplete_location(query)
                ret_val = []
                for location in res:
                    ret_val.append(self.location_search_repo.add_location(location))
                return ret_val
            else:
                return res

    def subscribe_to_location(self, user: User, place_id: str) -> bool | None:
        location = self.get_location_data(place_id)
        if location is None:
            return None
        if self.subscription_repo.get_by_user_and_location_id(user.id, location.id) is not None:
            return True
        return self.subscription_repo.create(LocationSubscription(user_id=user.id, location_id=location.id))

    def unsubscribe_from_location(self, user: User, place_id: str) -> bool | None:
        location = self.location_storage.get_location_by_place_id(place_id)
        if location is None:
            return None
        subscription = self.subscription_repo.get_by_user_and_location_id(user.id, location.id)
        if subscription is None or subscription.user_id != user.id:
            return None
        return self.subscription_repo.delete(subscription)

    def get_saved_locations(self, user: User, page: int = 1, page_size: int = 25) -> list[dict] | None:
        if page < 1 or page_size < 1:
            raise ValueError("page and page_size must be positive")
        subscriptions = self.subscription_repo.get_by_user_id(user.id, page, page_size)
        if subscriptions is None:
            return None
        locations = []
        for subscription in subscriptions:
            location = self.location_storage.get_location(subscription.location_id)
            if location is None:
                return None
            details = json.loads(location.details) if isinstance(location.details, str) else location.details
            locations.append({
                "id": location.place_id,
                "name": details.get("name") or details.get("formatted", ""),
                "formatted": details.get("formatted", ""),
                "lat": details["lat"],
                "lon": details["lon"],
            })
        return locations
