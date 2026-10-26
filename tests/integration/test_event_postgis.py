"""Run with POSTGIS_TEST_DATABASE_URI set to a database containing PostGIS.

All DDL and data live in a temporary schema inside a rolled-back transaction.
"""
from datetime import datetime, timedelta, timezone
from dataclasses import replace
import base64
import json
import os
from unittest.mock import Mock, call
from types import SimpleNamespace
from uuid import uuid4

from geoalchemy2 import WKTElement
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.database_models.events.event_model import EventModel, event_collaborators, event_tags
from app.database_models.location_model import LocationModel
from app.database_models.site_account.site_account_model import SiteAccountModel
from app.database_models.tags.tag_model import TagModel
from app.database_models.user_model import UserModel
from app.database_models.subscriptions.event_subscription_model import EventSubscriptionModel
from app.database_models.subscriptions.site_account_subscription_model import SiteAccountSubscriptionModel
from app.domain_models.Location import Location
from app.domain_models.events.event import Event
from app.domain_models.events.event_query import EventQuery
from app.extensions import db
from app.repositories.storage.events.sql_event_repo import SqlEventRepo
from app.repositories.storage.image.mem_image_storage import InMemoryImageStorage
from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo
from app.repositories.storage.sql_location_repo import SQLLocationRepo
from app.repositories.storage.sql_user_repo import SqlUserRepo
from app.services.event_service import EventService
from app.services.image_service import ImageService
from app.services.location_service import LocationService
from app.services.site_account_service import SiteAccountService
from app.services.password_service import PasswordService
from app.services.tag_service import TagService
from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo


@pytest.fixture
def postgis_session():
    uri = os.environ.get("POSTGIS_TEST_DATABASE_URI")
    if not uri:
        pytest.skip("Set POSTGIS_TEST_DATABASE_URI to run PostGIS integration tests")
    engine = create_engine(uri)
    schema = "event_test_" + uuid4().hex
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
                connection.exec_driver_sql(f'SET LOCAL search_path TO "{schema}", public')
                # Force creation in this schema even if public has tables of the same name.
                db.metadata.create_all(connection, checkfirst=False, tables=[
                    UserModel.__table__, SiteAccountModel.__table__, TagModel.__table__,
                    LocationModel.__table__, EventModel.__table__, event_tags, event_collaborators,
                    EventSubscriptionModel.__table__, SiteAccountSubscriptionModel.__table__,
                ])
                with Session(connection) as session:
                    yield session
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def postgis_repo(postgis_session):
    session = postgis_session
    session.add_all([
        SiteAccountModel(name="owner"), TagModel(name="Gaming"), TagModel(name="Dogs"),
        LocationModel(place_id="near", details="{}", geometry=WKTElement("POINT(13.405 52.52)", srid=4326)),
        LocationModel(place_id="far", details="{}", geometry=WKTElement("POINT(2.35 48.85)", srid=4326)),
        LocationModel(place_id="city", details="{}", geometry=WKTElement(
            "POLYGON((13 52,14 52,14 53,13 53,13 52))", srid=4326,
        )),
    ])
    session.commit()
    repo = SqlEventRepo(session)
    start = datetime(2026, 10, 22, 18, tzinfo=timezone.utc)
    for name, place, tags, access in [
        ("both", "near", [1, 2], ["wheelchair", "adults"]),
        ("dogs", "near", [2], ["wheelchair", "adults"]),
        ("gaming", "near", [1], ["wheelchair", "adults"]),
        ("fallback", "near", [], ["wheelchair", "adults"]),
        ("inaccessible", "near", [1, 2], ["adults"]),
        ("wrong-age", "near", [1, 2], ["wheelchair"]),
        ("far", "far", [1, 2], ["wheelchair", "adults"]),
    ]:
        repo.create_event(Event(
            name=name, description="test", from_=start, till=start + timedelta(hours=2),
            tags=tags, place_id=place, owner_id=1, layout=1, data=[], detail_data=[], access=access,
        ))
    return repo


def test_radius_access_ranking_and_pagination(postgis_repo):
    query = EventQuery(
        included_tags=[1, 2], access=["wheelchair", "adults"],
        longitude=13.405, latitude=52.52, radius_m=1000, include_partial=True,
    )
    assert [event.name for event in postgis_repo.query_events(query, 1, 10)] == [
        "both", "dogs", "gaming", "fallback",
    ]
    assert [event.name for event in postgis_repo.query_events(query, 2, 2)] == ["gaming", "fallback"]
    query.included_tags = [1]
    query.excluded_tags = [2]
    assert [event.name for event in postgis_repo.query_events(query, 1, 10)] == ["gaming", "fallback"]


def test_place_geometry_and_geojson_fence(postgis_repo):
    query = EventQuery(place_id="city", access=["wheelchair", "adults"])
    assert {event.name for event in postgis_repo.query_events(query, 1, 20)} == {
        "both", "dogs", "gaming", "fallback",
    }
    query.place_id = None
    query.geofence = {"type": "Polygon", "coordinates": [
        [[13, 52], [14, 52], [14, 53], [13, 53], [13, 52]],
    ]}
    assert {event.name for event in postgis_repo.query_events(query, 1, 20)} == {
        "both", "dogs", "gaming", "fallback",
    }


def test_use_case_create_site_accounts_publish_event_and_find_it(postgis_session):
    """An organizer and collaborator publish an accessible event at a new place."""
    session = postgis_session
    users = SqlUserRepo(session)
    sites = SqlSiteAccountRepo(session)
    locations = SQLLocationRepo(session)
    storage = InMemoryImageStorage("use-case-images")
    images = ImageService(storage, base_url="https://test.example")
    search = Mock()
    site_service = SiteAccountService(sites, users, images, search, application_repo=None)
    location_api = Mock()
    location_api.get_location_details.side_effect = lambda place_id: {
        "features": [{
            "properties": {"name": place_id},
            "geometry": {
                "type": "Point",
                "coordinates": [13.405, 52.52] if place_id == "new-venue" else [2.35, 48.85],
            },
        }],
    }
    location_service = LocationService(None, location_api, locations)
    event_service = EventService(SqlEventRepo(session), location_service, images)

    # Deliberately make the creator's user ID different from the owner's site ID.
    assert users.create_user("unrelated@example.com", "unused-test-hash")
    assert users.create_user("organizer@example.com", "unused-test-hash")
    creator = users.get_user_by_email("organizer@example.com")
    assert site_service.create_site_account("Community organizer", creator)
    assert site_service.create_site_account("Community collaborator", creator)
    owner = sites.get_site_account_by_name("Community organizer")
    collaborator = sites.get_site_account_by_name("Community collaborator")
    assert owner.id != creator.id
    assert owner.creator_id == collaborator.creator_id == creator.id
    assert owner.layout == collaborator.layout == "[]"
    assert owner.profile_picture is None
    assert search.add_site_account.call_count == 2

    png = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aT1sAAAAASUVORK5CYII="
    )
    image_data = "data:image/png;base64," + base64.b64encode(png).decode()
    assert site_service.modify_site_account(
        owner, layout=[{"image": image_data}], profile_picture=image_data,
    )
    owner = site_service.get_site_account_by_id(owner.id)
    assert owner.name == "Community organizer"
    assert owner.profile_picture.startswith("https://test.example/v1/image/site_account/")
    assert json.loads(owner.layout)[0]["image"].startswith("https://test.example/v1/image/")
    assert storage.get_image(owner.profile_picture.split("/v1/image/")[1]) == (png, "image/png")

    music, art, excluded = TagModel(name="Music"), TagModel(name="Art"), TagModel(name="Excluded")
    session.add_all([music, art, excluded])
    session.commit()
    start = datetime(2026, 10, 22, 18, tzinfo=timezone.utc)
    published = Event(
        name="Community concert", description="An accessible concert",
        from_=start, till=start + timedelta(hours=2),
        tags=[music.id, art.id], place_id="new-venue", layout=1,
        data=[{"image": image_data}, {"image": "https://example.com/banner.png"}],
        detail_data=[{"items": [{"image": image_data}]}],
        owner_id=owner.id, collaborators=[collaborator.id], access=["wheelchair", "adults"],
    )
    assert locations.get_location_by_place_id("new-venue") is None
    assert event_service.create_event(published)
    assert published.id is not None
    assert locations.get_location_by_place_id("new-venue") is not None

    # Matching and nonmatching events prove the query actually filters its results.
    second = replace(published, id=None, name="Community art show", tags=[art.id])
    assert event_service.create_event(second)
    for control in [
        replace(published, id=None, name="Community inaccessible concert", access=["adults"]),
        replace(published, id=None, name="Community distant concert", place_id="far-venue"),
        replace(published, id=None, name="Community excluded concert", tags=[music.id, excluded.id]),
    ]:
        assert event_service.create_event(control)

    # Re-read committed data, rather than relying on the ORM identity map.
    session.expire_all()
    saved = event_service.get_event_by_id(published.id)
    assert saved.name == published.name
    assert saved.description == published.description
    assert saved.from_ == start and saved.till == start + timedelta(hours=2)
    assert saved.owner_id == owner.id
    assert saved.collaborators == [collaborator.id]
    assert saved.tags == sorted([music.id, art.id])
    assert saved.place_id == "new-venue"
    assert saved.access == ["wheelchair", "adults"]
    assert saved.data[1]["image"] == "https://example.com/banner.png"
    for url in [saved.data[0]["image"], saved.detail_data[0]["items"][0]["image"]]:
        assert url.startswith("https://test.example/v1/image/events/")
        assert storage.get_image(url.split("/v1/image/")[1]) == (png, "image/png")

    query = EventQuery(
        included_tags=[music.id, art.id], excluded_tags=[excluded.id],
        organizer_ids=[owner.id], collaborator_ids=[collaborator.id],
        name="Community", access=["wheelchair", "adults"],
        from_=start, till=start + timedelta(hours=3),
        longitude=13.405, latitude=52.52, radius_m=1000,
    )
    first_page = event_service.query_events(query, page=1, page_size=1)
    second_page = event_service.query_events(query, page=2, page_size=1)
    assert [event.id for event in first_page] == [published.id]
    assert [event.id for event in second_page] == [second.id]
    assert event_service.query_events(query, page=3, page_size=1) == []
    # Shared venue data is fetched only once despite multiple event creations.
    assert location_api.get_location_details.call_args_list == [call("new-venue"), call("far-venue")]


@pytest.mark.parametrize("details_available", [True, False])
def test_http_create_site_publish_query_edit_and_delete_event(postgis_session, app, details_available):
    session = postgis_session
    users = SqlUserRepo(session)
    assert users.create_user("moderator@example.com", "test-hash")
    assert users.create_user("owner@example.com", "test-hash")
    owner = users.get_user_by_email("owner@example.com")
    moderator = users.get_user_by_email("moderator@example.com")
    moderator.role = 1
    users.update_user(moderator)
    images = ImageService(InMemoryImageStorage("http-use-case"), base_url="https://test.example")
    sites = SqlSiteAccountRepo(session)
    api = Mock()
    api.get_location_details.return_value = {"features": [{
        "properties": {"name": "Venue"}, "geometry": {"type": "Point", "coordinates": [13.4, 52.5]},
    }]}
    search = Mock()
    search.get_location_by_place_id.return_value = {
        "id": "new-venue", "name": "Venue", "lon": 13.4, "lat": 52.5,
    }
    if not details_available:
        api.get_location_details.return_value = {"type": "FeatureCollection", "features": []}
    app.user_service = SimpleNamespace(get_user=users.get_user)
    app.site_account_service = SiteAccountService(sites, users, images, Mock(), None)
    app.location_service = LocationService(search, api, SQLLocationRepo(session))
    app.event_service = EventService(SqlEventRepo(session), app.location_service, images)
    app.tag_service = TagService(SqlTagRepo(session), None, None, Mock())
    app.config["SERVER_NAME"] = "127.0.0.1:5000"
    client = app.test_client()
    owner_auth = {"Authorization": "Bearer " + PasswordService.generate_access_token(owner.id)}
    mod_auth = {"Authorization": "Bearer " + PasswordService.generate_access_token(moderator.id)}
    for name in ("Organizer", "Collaborator"):
        response = client.post("/v1/site_accounts", json={"name": name, "creator_id": owner.id}, headers=mod_auth)
        assert response.status_code == 200, response.json
    organizer = sites.get_site_account_by_name("Organizer")
    collaborator = sites.get_site_account_by_name("Collaborator")
    image = "data:image/png;base64,aGVsbG8="
    response = client.patch(f"/v1/site_accounts/{organizer.id}", headers=owner_auth, json={
        "picture": image, "banner": image, "colors": ["#abcdef"],
        "contact": [{"type": "email", "adress": "owner@example.com"}], "description": "Organizer details",
    })
    assert response.status_code == 200, response.json
    site_path = f"/v1/site_accounts/{organizer.id}"
    assert client.get(site_path).status_code == 404
    response = client.get(site_path, headers=owner_auth)
    assert response.status_code == 200, response.json
    details = response.json
    assert details["picture"].startswith("https://test.example/v1/image/")
    assert details["banner"].startswith("https://test.example/v1/image/")
    tag = TagModel(name="Music")
    session.add(tag)
    session.commit()
    payload = {
        "name": "Live music", "description": "A concert", "from": "2026-10-22T18:00:00Z",
        "till": "2026-10-22T20:00:00Z", "tags": [tag.id, "New concert tag"], "place-id": "new-venue", "layout": 1,
        "data": [{"image": image}], "detail-data": [], "owner-id": organizer.id,
        "collaborators": [collaborator.id], "access": ["wheelchair"],
    }
    response = client.post("/v1/event", json=payload, headers=owner_auth)
    assert response.status_code == 201, response.json
    created_tag = session.query(TagModel).filter_by(name="New concert tag").one()
    assert created_tag.parent_id is None
    app.tag_service.search_engine_repo.add_tag.assert_called_once()
    response = client.get("/v1/event", headers=owner_auth, query_string={
        "included_tags": tag.id, "access": "wheelchair", "organisers": organizer.id,
        "long": 13.4, "lat": 52.5, "radius": 1000, "page": 1, "size": 1,
    })
    assert response.status_code == 200, response.json
    assert len(response.json) == 1
    result = response.json[0]
    assert result["tags"] == sorted([tag.id, created_tag.id])
    assert result["owner-name"] == "Organizer"
    assert result["owner-picture"] == details["picture"]
    assert result["collaborators"][0]["collaborator-name"] == "Collaborator"
    assert result["place-data"]["name"] == "Venue"
    assert result["data"][0]["image"].startswith("https://test.example/v1/image/events/")
    event_id = result["id"]
    response = client.patch(f"/v1/event/{event_id}", headers=owner_auth, json={"name": "Updated concert", "data": []})
    assert response.status_code == 200, response.json
    assert client.get(f"/v1/event/{event_id}").json["name"] == "Updated concert"
    assert client.delete(f"/v1/event/{event_id}", headers=owner_auth).status_code == 200
    assert client.get(f"/v1/event/{event_id}").status_code == 404
    api.get_location_details.assert_called_once_with("new-venue")
    if details_available:
        search.get_location_by_place_id.assert_not_called()
    else:
        search.get_location_by_place_id.assert_called_once_with("new-venue")


def test_site_account_details_migration_preserves_existing_account(postgis_session):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from alembic.script import ScriptDirectory

    session = postgis_session
    session.add(SiteAccountModel(name="Existing organizer", profile_picture="https://example.com/profile.png"))
    session.commit()
    session.expunge_all()
    connection = session.connection()
    # Recreate the schema shape immediately before the new migration.
    for column in ("banner", "colors", "contact", "description", "visible"):
        connection.exec_driver_sql(f'ALTER TABLE site_accounts DROP COLUMN "{column}"')
    migration = ScriptDirectory("migrations").get_revision("c7e2a94b106d").module
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        row = connection.exec_driver_sql(
            "SELECT name, profile_picture, banner, colors, contact, description, visible FROM site_accounts"
        ).one()
        assert tuple(row) == ("Existing organizer", "https://example.com/profile.png", "", [], [], "", True)
        migration.downgrade()
        assert connection.exec_driver_sql("SELECT name, profile_picture FROM site_accounts").one() == (
            "Existing organizer", "https://example.com/profile.png",
        )


def test_location_repository_crud(postgis_session):
    repo = SQLLocationRepo(postgis_session)
    assert repo.get_location(999) is None
    assert repo.get_location_by_place_id('missing') is None
    missing = Location(id=999, place_id='missing', details={}, geometry=None)
    assert not repo.remove_location(missing)
    assert not repo.update_location(missing)
    location = Location(id=-1, place_id='test-place', details={'name': 'Berlin'},
                        geometry=WKTElement('POINT(13 52)', srid=4326))
    assert repo.add_location(location)
    assert location.id > 0
    assert not repo.add_location(location)
    assert json.loads(repo.get_location(location.id).details) == {'name': 'Berlin'}
    location.details = {'name': 'Updated'}
    assert repo.update_location(location)
    assert json.loads(repo.get_location_by_place_id('test-place').details) == {'name': 'Updated'}
    location.details = '{"name": "Serialized"}'
    assert repo.update_location(location)
    assert json.loads(repo.get_location(location.id).details) == {'name': 'Serialized'}
    assert repo.remove_location(location)
    assert repo.get_location(location.id) is None
