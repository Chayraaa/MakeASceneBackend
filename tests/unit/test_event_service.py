from copy import deepcopy
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery
from app.repositories.storage.image.mem_image_storage import InMemoryImageStorage
from app.services.event_service import EventService
from app.services.image_service import ImageService


@pytest.fixture
def event_value():
    return Event(
        name="Music", description="Live", from_=datetime(2026, 10, 22, 18, tzinfo=timezone.utc),
        till=datetime(2026, 10, 22, 20, tzinfo=timezone.utc), tags=[1], place_id="geoapify-id",
        layout=1, data=[{"image": "data:image/png;base64,aGVsbG8="}], owner_id=1,
        access=["wheelchair"], detail_data=[{"image": "https://example.com/image.png"}],
    )


def test_create_resolves_location_before_saving_and_converts_images(event_value):
    repo, locations = Mock(), Mock()
    storage = InMemoryImageStorage("images")
    service = EventService(repo, locations, ImageService(storage))

    def create(prepared):
        locations.get_location_data.assert_called_once_with("geoapify-id")
        assert prepared.data[0]["image"].startswith("http://127.0.0.1:5000/v1/image/events/")
        assert prepared.detail_data == [{"image": "https://example.com/image.png"}]
        prepared.id = 42
        return True

    repo.create_event.side_effect = create
    assert service.create_event(event_value)
    assert event_value.id == 42
    key = event_value.data[0]["image"].split("/v1/image/")[1]
    assert storage.get_image(key) == (b"hello", "image/png")


def test_failed_create_does_not_mutate_input(event_value):
    repo = Mock()
    repo.create_event.return_value = False
    service = EventService(repo, Mock(), ImageService(InMemoryImageStorage("images")))
    assert not service.create_event(event_value)
    assert event_value.id is None
    assert event_value.data[0]["image"].startswith("data:image/")


def test_missing_location_prevents_create(event_value):
    repo, locations, images = Mock(), Mock(), Mock()
    locations.get_location_data.return_value = None
    service = EventService(repo, locations, images)
    with pytest.raises(ValueError, match="location"):
        service.create_event(event_value)
    images.replace_event_images.assert_not_called()
    repo.create_event.assert_not_called()


def test_missing_update_does_not_upload(event_value):
    repo, images = Mock(), Mock()
    repo.get_event_by_id.return_value = None
    event_value.id = 999
    assert not EventService(repo, Mock(), images).update_event(event_value)
    images.replace_event_images.assert_not_called()


def test_query_resolves_fence_and_delegates_pagination():
    repo, locations = Mock(), Mock()
    repo.query_events.return_value = []
    query = EventQuery(place_id="city", access=["wheelchair"], include_partial=True)
    service = EventService(repo, locations, Mock())
    assert service.query_events(query, page=2, page_size=10) == repo.query_events.return_value
    locations.get_location_data.assert_called_once_with("city")
    repo.query_events.assert_called_once_with(query, 2, 10)


@pytest.mark.parametrize("query", [
    EventQuery(longitude=13, latitude=52), EventQuery(radius_m=-1, longitude=13, latitude=52),
    EventQuery(longitude=181, latitude=52, radius_m=100),
    EventQuery(included_tags=[1], excluded_tags=[1]),
    EventQuery(from_=datetime(2026, 1, 1)),
    EventQuery(geofence={"type": "Point", "coordinates": [13, 52]}),
])
def test_invalid_query_is_rejected(query):
    repo = Mock()
    with pytest.raises(ValueError):
        EventService(repo, Mock(), Mock()).query_events(query)
    repo.query_events.assert_not_called()


@pytest.mark.parametrize('field,value', [('from_', datetime(2026, 1, 1)), ('till', datetime(2026, 1, 1)),
                                        ('till', datetime(2025, 1, 1, tzinfo=timezone.utc))])
def test_invalid_event_dates_do_not_resolve_or_upload(event_value, field, value):
    repo, locations, images = Mock(), Mock(), Mock()
    setattr(event_value, field, value)
    with pytest.raises(ValueError):
        EventService(repo, locations, images).create_event(event_value)
    locations.get_location_data.assert_not_called()
    images.replace_event_images.assert_not_called()
    repo.create_event.assert_not_called()


@pytest.mark.parametrize('success', [False, True])
def test_update_preserves_input_until_repository_succeeds(event_value, success):
    repo = Mock()
    repo.update_event.return_value = success
    event_value.id = 1
    repo.get_event_by_id.return_value = deepcopy(event_value)
    service = EventService(repo, Mock(), ImageService(InMemoryImageStorage('images')))
    assert service.update_event(event_value) is success
    assert event_value.data[0]['image'].startswith('http' if success else 'data:image/')
    assert repo.update_event.call_args.args[0] is not event_value


def test_update_without_id_never_calls_repository(event_value):
    repo = Mock()
    assert EventService(repo, Mock(), Mock()).update_event(event_value) is False
    repo.get_event_by_id.assert_not_called()


@pytest.mark.parametrize('page,size', [(0, 25), (1, 0), (-1, 1)])
def test_invalid_pagination_does_not_query(page, size):
    repo = Mock()
    with pytest.raises(ValueError):
        EventService(repo, Mock(), Mock()).query_events(page=page, page_size=size)
    repo.query_events.assert_not_called()


def test_unresolved_query_location_does_not_query():
    repo, locations = Mock(), Mock()
    locations.get_location_data.return_value = None
    with pytest.raises(ValueError, match='location'):
        EventService(repo, locations, Mock()).query_events(EventQuery(place_id='unknown'))
    repo.query_events.assert_not_called()


def test_default_query_read_and_delete(event_value):
    repo = Mock()
    repo.query_events.return_value = []
    service = EventService(repo, Mock(), Mock())
    assert service.query_events() == []
    assert repo.query_events.call_args.args == (EventQuery(), 1, 25)
    assert service.get_event_by_id(123) is repo.get_event_by_id.return_value
    event_value.id = 123
    repo.get_event_by_id.return_value = event_value
    repo.remove_event.return_value = True
    assert service.remove_event(event_value) is True
