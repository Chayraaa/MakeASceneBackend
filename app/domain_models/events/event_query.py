from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import Any

from shapely.geometry import shape


@dataclass
class EventQuery:
    """Included tags use OR and rank by match count; other filters are mandatory.

    Dates select overlapping events. Radius is in metres; coordinates are (lon, lat).
    A place_id uses the cached place geometry as a fence. GeoJSON fences must be
    Polygon/MultiPolygon geometries in EPSG:4326. Access requires every supplied label.
    include_partial additionally admits events matching none of the included tags.
    Equally strong matches favor the last selected tag, then date/time.
    """

    included_tags: list[int] = field(default_factory=list)
    excluded_tags: list[int] = field(default_factory=list)
    access: list[str] = field(default_factory=list)
    name: str | None = None
    from_: datetime | None = None
    till: datetime | None = None
    place_id: str | None = None
    geofence: dict[str, Any] | None = None
    longitude: float | None = None
    latitude: float | None = None
    radius_m: float | None = None
    include_partial: bool = False
    organizer_ids: list[int] = field(default_factory=list)
    collaborator_ids: list[int] = field(default_factory=list)

    def validate(self):
        if set(self.included_tags) & set(self.excluded_tags):
            raise ValueError("A tag cannot be both included and excluded")
        for value in (self.from_, self.till):
            if value is not None and (value.tzinfo is None or value.utcoffset() is None):
                raise ValueError("Query dates must include a timezone")
        if self.from_ is not None and self.till is not None and self.from_ > self.till:
            raise ValueError("from must not be after till")
        coordinates = (self.longitude, self.latitude, self.radius_m)
        if any(value is not None for value in coordinates):
            if not all(value is not None and math.isfinite(value) for value in coordinates):
                raise ValueError("Radius requires finite longitude, latitude and radius_m")
            if not -180 <= self.longitude <= 180 or not -90 <= self.latitude <= 90:
                raise ValueError("Coordinates are outside longitude/latitude bounds")
            if self.radius_m < 0:
                raise ValueError("radius_m must not be negative")
        if self.geofence is not None:
            geometry = shape(self.geofence)
            if geometry.geom_type not in ("Polygon", "MultiPolygon") or geometry.is_empty or not geometry.is_valid:
                raise ValueError("Geofence must be a valid nonempty Polygon or MultiPolygon")
            min_x, min_y, max_x, max_y = geometry.bounds
            if not (-180 <= min_x <= max_x <= 180 and -90 <= min_y <= max_y <= 90):
                raise ValueError("Geofence coordinates must be longitude/latitude")
