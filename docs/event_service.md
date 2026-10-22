# Event service

`app.event_service` provides `create_event(Event)`, `get_event_by_id(id)`,
`update_event(Event)`, `remove_event(Event)`, and
`query_events(EventQuery(...), page=1, page_size=25)`. Writes return booleans;
creation assigns the generated ID to the supplied domain object. Queries return
domain events and paginate in SQL. Dates must include a timezone.

```python
from app.domain_models.events.event_query import EventQuery

events = app.event_service.query_events(
    EventQuery(
        included_tags=[1, 2],
        excluded_tags=[3],
        access=["wheelchair"],
        longitude=13.405,
        latitude=52.52,
        radius_m=5000,
    ),
    page=1,
    page_size=25,
)
```

Included tags use OR. More matched tags rank first. Among equally strong matches,
the last selected tag has priority: `[Gaming, Dogs]` ranks both, then Dogs, then
Gaming. Within each group, earlier event starts rank first, then event IDs for
stable pagination. `include_partial=True` also includes events
with no included tag matches, after matching events. Excluded tags and every
requested accessibility label always apply, including to fallback results.
Labels match the strings stored in `Event.access` exactly.

`organizer_ids` filters event owners and `collaborator_ids` filters collaborating
site accounts. Both accept lists of site-account IDs, using OR within each list.
When both are supplied, an event must match both filters. Empty lists apply no
restriction. These filters remain mandatory with `include_partial=True`.

```python
EventQuery(organizer_ids=[10, 11], collaborator_ids=[20])
```

This finds events owned by site account 10 or 11 that also have site account 20
as a collaborator.

`name` matches a case-insensitive literal substring. `from_` and `till` select
events overlapping the requested interval, including its boundaries. All supplied
filters combine with AND. Recurrence is stored as a duration string; this query
does not expand recurring events into occurrences.

For location filtering, supply `place_id` to use that place's cached geometry,
`geofence` as a GeoJSON Polygon/MultiPolygon, or longitude/latitude with `radius_m`.
Coordinates use EPSG:4326; radii use metres through PostGIS geography. Fences use
intersection, including their boundaries. Unknown place IDs are resolved through
`LocationService.get_location_data` before querying or writing events.
If Geoapify Place Details supplies no geometry for an autocomplete ID, the exact
cached autocomplete result supplies address data and a point geometry. This
fallback does not invent an area boundary.

Event `data` and `detail_data` are traversed recursively. Base64 image data URLs
are stored under `events/` and replaced with image URLs; existing URLs are
preserved. Site-account `picture` and `banner` accept HTTP(S) URLs or base64 image
data URLs on PATCH, and can be cleared with an empty string. Images are uploaded
before database writes; a failed write may leave an unused stored image.

Apply the site-account migrations before deploying. The event query uses
PostgreSQL/PostGIS directly and does not require a Typesense event collection.

## HTTP API

`/v1/event` supports POST and paginated GET; `/v1/event/{id}` supports GET,
PATCH, and DELETE. Every endpoint validates requests against the OpenAPI spec.
Fetching a single event is public. Querying requires authentication, as declared
in the spec. Writes require the user to own the event's owning site account or
have moderator-or-higher rank. Collaborators cannot edit solely by being listed.
Changing `owner-id` requires permission for both the old and new site accounts.

On event POST/PATCH, integer tags refer to existing IDs. String tags are names
(even numeric strings): missing names are created without parents through
`TagService.create_tag`, including search indexing. Existing names are reused;
duplicate IDs/names produce a single event-tag association. Responses contain IDs.

Query parameters follow the spec: `included_tags`, `excluded_tags`, `access`,
`name`, `from`, `till`, `place-id`, `long`, `lat`, `radius`,
`include-no-tag-matches`, `organisers`, `page`, and `size`. Array parameters use
repeated keys, for example `included_tags=1&included_tags=2`.

Event responses include owner and collaborator names/pictures plus `place-data`.
Site-account PATCH supports `creator_id`, `name`, `layout`, `picture`, `banner`,
`colors`, `contact`, `description`, and `visible`; contact objects retain the
spec's `adress` spelling. Invisible accounts are omitted from public search results.
