from geoalchemy2.shape import from_shape

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
    def get_location_data(self, place_id: str) -> Location:
        location = self.location_storage.get_location_by_place_id(place_id)
        if location is not None:
            return location

        resp = self.location_api_repo.get_location_details(place_id)
        # Process location data
        details = resp["features"][0]["properties"]
        geometry = resp["features"][0]["geometry"]["coordinates"]
        s = shape(geometry)
        geo_obj = from_shape(s, srid=4326)
        location = Location(id=-1, place_id=place_id, details=details, geometry=geo_obj)
        if location is not None:
            self.location_storage.add_location(location)
            return location

        return None


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