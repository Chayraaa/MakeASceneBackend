from geoalchemy2.shape import from_shape
import math

from app.repositories.interfaces.external.search_engine_location_protocol import SearchEngineLocationProtocol
from app.repositories.interfaces.external.location_protocol import LocationProtocol
from app.domain_models.Location import Location
from shapely.geometry import shape
from app.repositories.interfaces.storage.location_storage_protocol import LocationStorageProtocol


class LocationService:
    def __init__(self, location_search_repo: SearchEngineLocationProtocol, location_api_repo: LocationProtocol, location_storage: LocationStorageProtocol):
        self.location_search_repo = location_search_repo
        self.location_api_repo = location_api_repo
        self.location_storage = location_storage

    # Fetches the location details:
    # Prio 1: Location DB Table
    # Prio 2: Location API
    def get_location_data(self, place_id: str) -> Location | None:
        location = self.location_storage.get_location_by_place_id(place_id)
        if location is not None:
            return location

        resp = self.location_api_repo.get_location_details(place_id)
        feature = next((item for item in resp.get("features", []) if item.get("geometry")), None)
        if feature is not None:
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
                return None
            try:
                longitude, latitude = float(cached["lon"]), float(cached["lat"])
            except (KeyError, TypeError, ValueError):
                return None
            if not (math.isfinite(longitude) and math.isfinite(latitude)
                    and -180 <= longitude <= 180 and -90 <= latitude <= 90):
                return None
            details = {key: value for key, value in cached.items() if key != "id"}
            details["place_id"] = place_id
            geometry = {"type": "Point", "coordinates": [longitude, latitude]}
        s = shape(geometry)
        geo_obj = from_shape(s, srid=4326)
        location = Location(id=-1, place_id=place_id, details=details, geometry=geo_obj)
        if not self.location_storage.add_location(location):
            return self.location_storage.get_location_by_place_id(place_id)
        return location


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
