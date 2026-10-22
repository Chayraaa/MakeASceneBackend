import pytest
from unittest.mock import Mock

from geoalchemy2.shape import to_shape

from app.services.location_service import LocationService


def test_location_cache_avoids_api():
    storage, api = Mock(), Mock()
    cached = storage.get_location_by_place_id.return_value
    assert LocationService(Mock(), api, storage).get_location_data("cached") is cached
    api.get_location_details.assert_not_called()


def test_missing_location_is_converted_from_geojson_and_stored():
    storage, api = Mock(), Mock()
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {"features": [{
        "properties": {"name": "Berlin"},
        "geometry": {"type": "Point", "coordinates": [13.4, 52.5]},
    }]}
    result = LocationService(Mock(), api, storage).get_location_data("geoapify-id")
    assert result.place_id == "geoapify-id"
    assert tuple(to_shape(result.geometry).coords)[0] == (13.4, 52.5)
    assert result.geometry.srid == 4326
    storage.add_location.assert_called_once_with(result)


def test_unresolved_location_is_not_stored():
    storage, api = Mock(), Mock()
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {}
    assert LocationService(Mock(), api, storage).get_location_data("missing") is None
    storage.add_location.assert_not_called()


def test_empty_place_details_uses_exact_autocomplete_result_and_caches_it():
    search, storage, api = Mock(), Mock(), Mock()
    place_id = "516fc8f5a56de22740598e55ef1582214940c00203"
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {"type": "FeatureCollection", "features": []}
    search.get_location_by_place_id.return_value = {
        "id": place_id, "formatted": "Example address", "lon": 13.4, "lat": 52.5,
    }
    service = LocationService(search, api, storage)
    result = service.get_location_data(place_id)
    assert result.place_id == place_id
    assert result.details["formatted"] == "Example address"
    assert result.details["place_id"] == place_id
    assert tuple(to_shape(result.geometry).coords)[0] == (13.4, 52.5)
    assert result.geometry.srid == 4326
    search.get_location_by_place_id.assert_called_once_with(place_id)
    storage.add_location.assert_called_once_with(result)
    storage.get_location_by_place_id.return_value = result
    assert service.get_location_data(place_id) is result
    api.get_location_details.assert_called_once_with(place_id)


def test_place_details_geometry_takes_priority_over_autocomplete():
    search, storage, api = Mock(), Mock(), Mock()
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {"features": [{
        "properties": {"name": "Area"}, "geometry": {"type": "Polygon", "coordinates": [
            [[13, 52], [14, 52], [14, 53], [13, 52]],
        ]},
    }]}
    result = LocationService(search, api, storage).get_location_data("area")
    assert to_shape(result.geometry).geom_type == "Polygon"
    search.get_location_by_place_id.assert_not_called()


def test_missing_autocomplete_result_remains_unresolved():
    search, storage, api = Mock(), Mock(), Mock()
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {"features": []}
    search.get_location_by_place_id.return_value = None
    assert LocationService(search, api, storage).get_location_data("unknown") is None
    storage.add_location.assert_not_called()


def test_invalid_cached_coordinates_are_not_stored():
    search, storage, api = Mock(), Mock(), Mock()
    storage.get_location_by_place_id.return_value = None
    api.get_location_details.return_value = {"features": []}
    for coordinates in ({}, {"lat": None, "lon": 13}, {"lat": 91, "lon": 13}, {"lat": 52, "lon": float("nan")}):
        search.get_location_by_place_id.return_value = coordinates
        assert LocationService(search, api, storage).get_location_data("invalid") is None
    storage.add_location.assert_not_called()


@pytest.mark.parametrize('force,cached', [(False, []), (False, [{'id': 'cached'}]), (True, [{'id': 'cached'}])])
def test_autocomplete_cache_and_force_api(force, cached):
    search, storage, api = Mock(), Mock(), Mock()
    search.autocomplete_location.return_value = cached
    api.autocomplete_location.return_value = [{'place_id': 'new'}]
    search.add_location.return_value = {'id': 'new'}
    result = LocationService(search, api, storage).autocomplete_location('Berlin', force)
    if force or not cached:
        assert result == [{'id': 'new'}]
        api.autocomplete_location.assert_called_once_with('Berlin')
        search.add_location.assert_called_once_with({'place_id': 'new'})
    else:
        assert result == cached
        api.autocomplete_location.assert_not_called()
    if force:
        search.autocomplete_location.assert_not_called()


def test_concurrent_location_insert_returns_winning_record():
    search, storage, api = Mock(), Mock(), Mock()
    winner = Mock()
    storage.get_location_by_place_id.side_effect = [None, winner]
    storage.add_location.return_value = False
    api.get_location_details.return_value = {'features': [{
        'properties': {'name': 'Berlin'}, 'geometry': {'type': 'Point', 'coordinates': [13, 52]},
    }]}
    assert LocationService(search, api, storage).get_location_data('p') is winner
