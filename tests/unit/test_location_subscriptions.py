import json
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain_models.subscriptions.location_subscription import LocationSubscription
from app.services.location_service import LocationService


@pytest.fixture
def context():
    storage, repo = Mock(), Mock()
    service = LocationService(Mock(), Mock(), storage, repo)
    user = SimpleNamespace(id=1)
    location = SimpleNamespace(id=7, place_id="place-123", details={"formatted": "Berlin", "lat": 52.5, "lon": 13.4})
    return service, storage, repo, user, location


def test_subscribe_resolves_place_id_and_is_idempotent(context):
    service, storage, repo, user, location = context
    service.get_location_data = Mock(return_value=location)
    repo.get_by_user_and_location_id.return_value = None
    repo.create.return_value = True
    assert service.subscribe_to_location(user, "place-123") is True
    service.get_location_data.assert_called_once_with("place-123")
    repo.create.assert_called_once_with(LocationSubscription(user_id=1, location_id=7))
    repo.create.reset_mock()
    repo.get_by_user_and_location_id.return_value = LocationSubscription(user_id=1, location_id=7)
    assert service.subscribe_to_location(user, "place-123") is True
    repo.create.assert_not_called()
    service.get_location_data.return_value = None
    assert service.subscribe_to_location(user, "missing") is None


def test_unsubscribe_only_current_user(context):
    service, storage, repo, user, location = context
    storage.get_location_by_place_id.return_value = location
    for subscription in (None, LocationSubscription(user_id=2, location_id=7)):
        repo.get_by_user_and_location_id.return_value = subscription
        assert service.unsubscribe_from_location(user, "place-123") is None
    repo.delete.assert_not_called()
    subscription = LocationSubscription(user_id=1, location_id=7)
    repo.get_by_user_and_location_id.return_value = subscription
    repo.delete.return_value = True
    assert service.unsubscribe_from_location(user, "place-123") is True
    repo.get_by_user_and_location_id.assert_called_with(1, 7)
    repo.delete.assert_called_once_with(subscription)
    service.location_api_repo.assert_not_called()


@pytest.mark.parametrize("serialized", [True, False])
def test_saved_location_details_and_pagination(context, serialized):
    service, storage, repo, user, location = context
    if serialized:
        location.details = json.dumps(location.details)
    storage.get_location.return_value = location
    repo.get_by_user_id.return_value = [LocationSubscription(user_id=1, location_id=7)]
    assert service.get_saved_locations(user, 2, 5) == [{"id": "place-123", "name": "Berlin", "formatted": "Berlin", "lat": 52.5, "lon": 13.4}]
    repo.get_by_user_id.assert_called_once_with(1, 2, 5)
    storage.get_location.assert_called_once_with(7)
    repo.get_by_user_id.return_value = None
    assert service.get_saved_locations(user) is None
    repo.get_by_user_id.return_value = []
    assert service.get_saved_locations(user) == []
    with pytest.raises(ValueError):
        service.get_saved_locations(user, 0)
