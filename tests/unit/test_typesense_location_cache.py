from unittest.mock import Mock

from typesense.exceptions import ObjectNotFound

from app.repositories.external.search_engine.typesense_location_search_repo import TypesenseLocationSearchRepo


def test_cached_location_lookup_uses_exact_place_id():
    client = Mock()
    client.collections = {"locations": Mock()}
    result = {"id": "place-id", "lat": 52.5, "lon": 13.4}
    documents = {"place-id": Mock()}
    client.collections["locations"].documents = documents
    documents["place-id"].retrieve.return_value = result
    repo = TypesenseLocationSearchRepo(client)
    repo._ensure_ready = Mock()
    assert repo.get_location_by_place_id("place-id") is result
    documents["place-id"].retrieve.assert_called_once_with()


def test_unknown_cached_location_returns_none():
    client = Mock()
    client.collections = {"locations": Mock()}
    client.collections["locations"].documents = {"unknown": Mock()}
    client.collections["locations"].documents["unknown"].retrieve.side_effect = ObjectNotFound("not found")
    repo = TypesenseLocationSearchRepo(client)
    repo._ensure_ready = Mock()
    assert repo.get_location_by_place_id("unknown") is None
