from app.repositories.interfaces.external.search_engine_location_protocol import SearchEngineLocationProtocol
from app.repositories.interfaces.external.location_protocol import LocationProtocol


class LocationService:
    def __init__(self, location_search_repo: SearchEngineLocationProtocol, location_api_repo: LocationProtocol):
        self.location_search_repo = location_search_repo
        self.location_api_repo = location_api_repo

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