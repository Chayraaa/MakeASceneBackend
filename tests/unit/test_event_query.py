from datetime import datetime, timezone

import pytest

from app.domain_models.events.event_query import EventQuery


@pytest.mark.parametrize('kwargs', [
    {'longitude': float('nan'), 'latitude': 52, 'radius_m': 1},
    {'longitude': 13, 'latitude': float('inf'), 'radius_m': 1},
    {'longitude': 13, 'latitude': 52, 'radius_m': float('inf')},
    {'longitude': 13, 'latitude': -91, 'radius_m': 1},
    {'longitude': -181, 'latitude': 52, 'radius_m': 1},
    {'from_': datetime(2026, 2, 1, tzinfo=timezone.utc), 'till': datetime(2026, 1, 1, tzinfo=timezone.utc)},
    {'till': datetime(2026, 1, 1)},
    {'geofence': {'type': 'Polygon', 'coordinates': []}},
    {'geofence': {'type': 'Polygon', 'coordinates': [[[0, 0], [1, 1], [0, 1], [1, 0], [0, 0]]]}},
    {'geofence': {'type': 'Polygon', 'coordinates': [[[181, 0], [182, 0], [182, 1], [181, 0]]]}},
])
def test_invalid_event_query(kwargs):
    with pytest.raises(ValueError):
        EventQuery(**kwargs).validate()


@pytest.mark.parametrize('longitude,latitude', [(-180, -90), (180, 90), (0, 0)])
def test_radius_boundaries_and_zero_radius(longitude, latitude):
    EventQuery(longitude=longitude, latitude=latitude, radius_m=0).validate()


@pytest.mark.parametrize('geometry_type', ['Polygon', 'MultiPolygon'])
def test_valid_fence(geometry_type):
    coords = [[[13, 52], [14, 52], [14, 53], [13, 52]]]
    EventQuery(geofence={'type': geometry_type, 'coordinates': coords if geometry_type == 'Polygon' else [coords]}).validate()
