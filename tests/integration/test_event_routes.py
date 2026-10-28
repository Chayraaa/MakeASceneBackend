from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
import yaml

from app.domain_models.events.event import Event
from app.domain_models.user import Role
from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo
from app.repositories.storage.sql_user_repo import SqlUserRepo
from app.database_models.tags.tag_model import TagModel
from app.domain_models.Location import Location
from app.services.event_service import EventService
from app.services.password_service import PasswordService


@pytest.fixture
def api(app, session):
    app.config["SERVER_NAME"] = "127.0.0.1:5000"
    users = SqlUserRepo(session)
    actors = {}
    for name, role in [("owner", 0), ("stranger", 0), ("collaborator", 0), ("moderator", 1), ("admin", 2)]:
        assert users.create_user(f"{name}@example.com", "test-hash")
        actor = users.get_user_by_email(f"{name}@example.com")
        actor.role = role
        users.update_user(actor)
        actors[name] = actor
    sites = SqlSiteAccountRepo(session)
    assert sites.create_site_account("Foreign site", actors["stranger"])
    assert sites.create_site_account("Owner site", actors["owner"])
    assert sites.create_site_account("Collaborating site", actors["collaborator"])
    owner = sites.get_site_account_by_name("Owner site")
    collaborator = sites.get_site_account_by_name("Collaborating site")
    foreign = sites.get_site_account_by_name("Foreign site")
    app.site_account_service.search_engine = Mock()
    app.tag_service.search_engine_repo = Mock()
    tag = TagModel(name="Music")
    session.add(tag)
    session.commit()
    start = datetime(2026, 10, 22, 18, tzinfo=timezone.utc)
    value = Event(
        id=123, name="Community concert", description="Live music", from_=start,
        till=start + timedelta(hours=2), tags=[tag.id], place_id="venue", layout=1,
        data=[{"image": "https://example.com/event.png"}], detail_data=[],
        owner_id=owner.id, collaborators=[collaborator.id], access=["wheelchair"],
    )
    app.event_service = Mock(spec=EventService)
    app.event_service.get_event_by_id.side_effect = lambda event_id: value if event_id == value.id else None
    app.event_service.create_event.return_value = True
    app.event_service.update_event.return_value = True
    app.event_service.remove_event.return_value = True
    app.event_service.leave_collaboration.return_value = False
    app.event_service.query_events.return_value = [value]
    app.location_service = Mock()
    app.location_service.get_location_data.return_value = Location(
        id=1, place_id="venue", details='{"name": "Concert hall"}', geometry=None,
    )
    return SimpleNamespace(
        app=app, client=app.test_client(), users=users, actors=actors, sites=sites, owner=owner,
        collaborator=collaborator, foreign=foreign, event=value, service=app.event_service,
    )


def authorization(api, actor="owner"):
    return {"Authorization": "Bearer " + PasswordService.generate_access_token(api.actors[actor].id)}


def event_payload(api):
    result = api.event.to_dict()
    result.pop("id")
    result.pop("repeating")
    return result


def assert_schema(api, response, name):
    with open(api.app.root_path + "/static/makeascene.openapi.yaml", encoding="utf-8") as source:
        spec = yaml.safe_load(source)
    registry = Registry().with_resource("urn:test-api", Resource(spec, DRAFT202012))
    Draft202012Validator(
        {"$ref": f"urn:test-api#/components/schemas/{name}"}, registry=registry,
        format_checker=FormatChecker(),
    ).validate(response.get_json())


@pytest.mark.parametrize("actor, expected", [("owner", 201), ("stranger", 401), ("collaborator", 401),
                                            ("moderator", 201), ("admin", 201)])
def test_create_event_permission(api, actor, expected):
    response = api.client.post("/v1/event", json=event_payload(api), headers=authorization(api, actor))
    assert response.status_code == expected, response.get_json()
    assert api.service.create_event.called == (expected == 201)
    if expected == 201:
        created = api.service.create_event.call_args.args[0]
        assert created.owner_id == api.owner.id
        assert created.collaborators == [api.collaborator.id]
        assert created.from_ == api.event.from_


@pytest.mark.parametrize("method", ["patch", "delete"])
@pytest.mark.parametrize("actor, expected", [("owner", 200), ("stranger", 401), ("collaborator", 401),
                                            ("moderator", 200), ("admin", 200)])
def test_event_write_permission(api, method, actor, expected):
    kwargs = {"json": {"name": "Changed"}} if method == "patch" else {}
    response = getattr(api.client, method)(
        "/v1/event/123", headers=authorization(api, actor), **kwargs,
    )
    assert response.status_code == expected, response.get_json()
    write = api.service.update_event if method == "patch" else api.service.remove_event
    assert write.called == (expected == 200)


@pytest.mark.parametrize("actor, expected", [("owner", 401), ("stranger", 401), ("moderator", 200), ("admin", 200)])
def test_event_transfer_requires_access_to_both_sites(api, actor, expected):
    response = api.client.patch(
        "/v1/event/123", json={"owner-id": api.foreign.id}, headers=authorization(api, actor),
    )
    assert response.status_code == expected
    assert api.service.update_event.called == (expected == 200)


def test_event_public_read_matches_spec(api):
    response = api.client.get("/v1/event/123")
    assert response.status_code == 200, response.get_json()
    assert_schema(api, response, "EventObject")
    assert response.json["owner-name"] == api.owner.name
    assert response.json["place-data"] == {"name": "Concert hall"}
    assert response.json["collaborators"][0]["collaborator-name"] == api.collaborator.name
    assert api.client.get("/v1/event/999").status_code == 404


def test_event_query_allows_anonymous_requests(api):
    response = api.client.get("/v1/event")

    assert response.status_code == 200
    assert len(response.get_json()) == 1
    assert api.service.query_events.call_args.kwargs == {
        "page": 1, "page_size": 25, "user": None,
    }


def test_event_query_maps_spec_parameters(api):
    response = api.client.get("/v1/event", headers=authorization(api), query_string=[
        ("included_tags", "1"), ("included_tags", "2"), ("excluded_tags", "3"),
        ("access", "wheelchair"), ("name", "Concert"),
        ("from", "2026-10-22T18:00:00Z"), ("till", "2026-10-22T22:00:00Z"),
        ("place-id", "berlin"), ("long", "13.4"), ("lat", "52.5"), ("radius", "1000"),
        ("include-no-tag-matches", "true"), ("organisers", str(api.owner.id)), ("page", "2"), ("size", "5"),
    ])
    assert response.status_code == 200, response.get_json()
    query = api.service.query_events.call_args.args[0]
    assert query.included_tags == [1, 2] and query.excluded_tags == [3]
    assert query.organizer_ids == [api.owner.id]
    assert query.access == ["wheelchair"] and query.name == "Concert"
    assert query.place_id == "berlin" and query.longitude == 13.4 and query.latitude == 52.5
    assert query.radius_m == 1000 and query.include_partial
    assert query.from_.tzinfo is not None
    assert api.service.query_events.call_args.kwargs == {"page": 2, "page_size": 5, "user": api.actors["owner"]}
    for value in response.json:
        single_response = SimpleNamespace(get_json=lambda: value)
        assert_schema(api, single_response, "EventObject")


@pytest.mark.parametrize("method, path", [("post", "/v1/event"), ("patch", "/v1/event/123"),
                                         ("delete", "/v1/event/123")])
def test_event_requires_authentication(api, method, path):
    response = getattr(api.client, method)(path, json={})
    assert response.status_code == 401
    api.service.create_event.assert_not_called()
    api.service.update_event.assert_not_called()
    api.service.remove_event.assert_not_called()
    api.service.query_events.assert_not_called()


@pytest.mark.parametrize("changes", [{"layout": "invalid"}, {"owner-id": "invalid"},
                                     {"from": "invalid"}, {"collaborators": ["invalid"]}])
def test_event_request_validation(api, changes):
    response = api.client.post("/v1/event", json={**event_payload(api), **changes}, headers=authorization(api))
    assert response.status_code == 422, response.get_json()
    api.service.create_event.assert_not_called()


def test_missing_event_and_site_references(api):
    for method in ("patch", "delete"):
        response = getattr(api.client, method)("/v1/event/999", json={}, headers=authorization(api))
        assert response.status_code == 404
    for field, value in [("owner-id", 999), ("tags", [999]), ("collaborators", [999])]:
        response = api.client.post(
            "/v1/event", json={**event_payload(api), field: value}, headers=authorization(api),
        )
        assert response.status_code == 404, response.get_json()
    api.service.create_event.assert_not_called()


def test_site_account_details_images_and_empty_updates(api):
    path = f"/v1/site_accounts/{api.owner.id}"
    response = api.client.patch(path, headers=authorization(api), json={
        "picture": "data:image/png;base64,aGVsbG8=", "banner": "data:image/png;base64,aGVsbG8=",
        "colors": ["#123456"], "contact": [{"type": "email", "adress": "hello@example.com"}],
        "description": "About the organizer", "visible": False,
    })
    assert response.status_code == 200, response.get_json()
    response = api.client.get(path, headers=authorization(api))
    assert_schema(api, response, "SiteAccount")
    assert response.json["picture"].startswith("http://127.0.0.1:5000/v1/image/site_account/")
    assert response.json["banner"].startswith("http://127.0.0.1:5000/v1/image/site_account/")
    assert response.json["contact"] == [{"type": "email", "adress": "hello@example.com"}]
    assert response.json["colors"] == ["#123456"] and response.json["visible"] is False
    response = api.client.patch(path, headers=authorization(api), json={
        "picture": "https://example.com/picture.png", "banner": "https://example.com/banner.png",
        "colors": [], "contact": [], "layout": [], "description": "", "visible": True,
    })
    assert response.status_code == 200
    result = api.client.get(path).json
    assert result["picture"] == "https://example.com/picture.png"
    assert result["banner"] == "https://example.com/banner.png"
    assert result["colors"] == result["contact"] == result["layout"] == []
    assert result["description"] == "" and result["visible"] is True


@pytest.mark.parametrize("actor, expected", [("owner", 200), ("stranger", 401), ("moderator", 200), ("admin", 200)])
def test_site_account_update_permissions(api, actor, expected):
    response = api.client.patch(
        f"/v1/site_accounts/{api.owner.id}", json={"description": "Changed"}, headers=authorization(api, actor),
    )
    assert response.status_code == expected


def test_site_creator_transfer_and_missing_creator(api):
    path = f"/v1/site_accounts/{api.owner.id}"
    response = api.client.patch(path, json={"creator_id": 999}, headers=authorization(api))
    assert response.status_code == 404
    response = api.client.patch(path, json={"creator_id": api.actors["stranger"].id}, headers=authorization(api))
    assert response.status_code == 200
    response = api.client.patch(path, json={"name": "No longer mine"}, headers=authorization(api))
    assert response.status_code == 401


def test_site_account_creation_is_moderator_only(api):
    payload = {"name": "New site", "creator_id": api.actors["owner"].id}
    assert api.client.post("/v1/site_accounts", json=payload, headers=authorization(api)).status_code == 401
    response = api.client.post("/v1/site_accounts", json=payload, headers=authorization(api, "admin"))
    assert response.status_code == 200, response.get_json()
    created = api.sites.get_site_account_by_name("New site")
    assert created.creator_id == api.actors["owner"].id
    assert_schema(api, api.client.get(f"/v1/site_accounts/{created.id}", headers=authorization(api)), "SiteAccount")


@pytest.mark.parametrize("method", ["post", "patch"])
def test_event_tag_names_are_created_indexed_and_reused(api, method):
    existing_id = api.event.tags[0]
    payload = {"tags": [existing_id, "New tag", "123", "New tag", "Music"]}
    if method == "post":
        payload = {**event_payload(api), **payload}
    path = "/v1/event" if method == "post" else "/v1/event/123"
    write = api.service.create_event if method == "post" else api.service.update_event
    response = getattr(api.client, method)(path, json=payload, headers=authorization(api))
    assert response.status_code == (201 if method == "post" else 200), response.json
    tags = api.app.tag_service.tag_repo
    new = tags.get_tag_by_name("New tag")
    numeric = tags.get_tag_by_name("123")
    assert new is not None and numeric is not None
    assert new.parent is None and numeric.parent is None
    assert write.call_args.args[0].tags == [existing_id, new.id, numeric.id]
    search = api.app.tag_service.search_engine_repo
    assert {args.args[0].name for args in search.add_tag.call_args_list} == {"New tag", "123"}
    assert search.add_tag.call_count == 2
    # A repeated request must not duplicate tags or index them again.
    response = getattr(api.client, method)(path, json=payload, headers=authorization(api))
    assert response.status_code == (201 if method == "post" else 200)
    assert search.add_tag.call_count == 2


@pytest.mark.parametrize("actor, changes, expected", [
    ("stranger", {}, 401),
    ("owner", {"collaborators": [999]}, 404),
    ("owner", {"tags": ["Should not be created", 999]}, 404),
    ("owner", {"tags": ["Should not be created", "   "]}, 422),
])
def test_invalid_or_unauthorized_event_does_not_create_tags(api, actor, changes, expected):
    payload = {**event_payload(api), "tags": ["Should not be created"], **changes}
    response = api.client.post("/v1/event", json=payload, headers=authorization(api, actor))
    assert response.status_code == expected, response.json
    assert api.app.tag_service.tag_repo.get_tag_by_name("Should not be created") is None
    api.app.tag_service.search_engine_repo.add_tag.assert_not_called()
    api.service.create_event.assert_not_called()


def test_create_art_event_with_only_new_tag_names(api):
    names = ["Art", "Illustration", "Community", "Queer"]
    payload = {
        **event_payload(api),
        "name": "Colors & Characters – Community Art Night",
        "description": "Ein kreativer Abend rund um digitale Illustration, Charakterdesign und queere Kunst.",
        "from": "2026-11-14T18:00:00+01:00",
        "till": "2026-11-14T23:00:00+01:00",
        "tags": names,
    }
    response = api.client.post("/v1/event", json=payload, headers=authorization(api))
    assert response.status_code == 201, response.json
    created_tags = [api.app.tag_service.tag_repo.get_tag_by_name(name) for name in names]
    assert all(tag is not None and tag.parent is None for tag in created_tags)
    saved_event = api.service.create_event.call_args.args[0]
    assert saved_event.tags == [tag.id for tag in created_tags]
    assert saved_event.from_.utcoffset() == timedelta(hours=1)
    assert api.app.tag_service.search_engine_repo.add_tag.call_count == 4


@pytest.mark.parametrize("actor,allowed", [(None, False), ("stranger", False), ("collaborator", False),
                                         ("owner", True), ("moderator", True), ("admin", True)])
@pytest.mark.parametrize("kind", ["event", "site_accounts"])
def test_hidden_detail_permissions(api, actor, allowed, kind):
    headers = authorization(api, actor) if actor else {}
    if kind == "event":
        api.event.visible = False
        real = EventService(Mock(), Mock(), Mock(), site_account_service=api.app.site_account_service)
        api.service.can_view.side_effect = real.can_view
        target_id = api.event.id
    else:
        target_id = api.owner.id  # New site accounts are hidden by default.
    response = api.client.get(f"/v1/{kind}/{target_id}", headers=headers)
    assert response.status_code == (200 if allowed else 404)


@pytest.mark.parametrize("actor,allowed", [(None, False), ("stranger", False), ("owner", True),
                                         ("moderator", True), ("admin", True)])
def test_site_search_visibility(api, actor, allowed):
    api.app.site_account_service.search_engine.search_by_semantic.return_value = [SimpleNamespace(id=api.owner.id)]
    headers = authorization(api, actor) if actor else {}
    response = api.client.get("/v1/site_accounts?q=Owner", headers=headers)
    assert response.status_code == 200
    assert [account["id"] for account in response.json] == ([api.owner.id] if allowed else [])


@pytest.mark.parametrize("zone", ["Europe/Berlin", "America/New_York", "UTC"])
def test_timezone_update_persisted_and_returned(api, zone):
    response = api.client.patch("/v1/users/me", headers=authorization(api), json={"timezone": zone})
    assert response.status_code == 200, response.json
    assert response.json["timezone"] == zone
    assert api.users.get_user(api.actors["owner"].id).timezone == zone
    response = api.client.get("/v1/users/me", headers=authorization(api))
    assert response.json["timezone"] == zone


@pytest.mark.parametrize("zone", ["Invalid/Zone", "", "../Europe/Berlin", None, 123])
def test_invalid_timezone_does_not_change_user(api, zone):
    before = api.users.get_user(api.actors["owner"].id)
    response = api.client.patch("/v1/users/me", headers=authorization(api),
                                json={"timezone": zone, "mature": not before.mature})
    assert response.status_code == 422
    after = api.users.get_user(before.id)
    assert (after.timezone, after.mature) == (before.timezone, before.mature)


@pytest.mark.parametrize("path", ["/v1/event/123", "/v1/site_accounts/1", "/v1/site_accounts?q=Owner"])
def test_optional_authentication_rejects_bad_tokens(api, path):
    assert api.client.get(path, headers={"Authorization": "Bearer invalid"}).status_code == 401


def test_owned_site_accounts_are_scoped_and_paginated(api):
    api.sites.create_site_account("Second owned site", api.actors["owner"])
    path = "/v1/users/me/site_accounts/owned"
    response = api.client.get(path, headers=authorization(api))
    assert response.status_code == 200
    assert [site["name"] for site in response.json] == ["Owner site", "Second owned site"]
    assert all(not site["visible"] for site in response.json)
    response = api.client.get(path + "?page=2&page_size=1", headers=authorization(api))
    assert [site["name"] for site in response.json] == ["Second owned site"]
    response = api.client.get(path, headers=authorization(api, "moderator"))
    assert response.json == []


def test_owned_events_response(api):
    api.service.get_owned_events.return_value = [api.event]
    response = api.client.get("/v1/users/me/events/owned?page=2&page_size=3", headers=authorization(api))
    assert response.status_code == 200
    assert response.json[0]["id"] == api.event.id
    assert response.json[0]["owner-name"] == api.owner.name
    with open(api.app.root_path + "/static/makeascene.openapi.yaml", encoding="utf-8") as source:
        spec = yaml.safe_load(source)
    registry = Registry().with_resource("urn:test-api", Resource(spec, DRAFT202012))
    Draft202012Validator(
        {"$ref": "urn:test-api#/paths/~1users~1me~1events~1owned/get/responses/200/content/application~1json/schema"},
        registry=registry, format_checker=FormatChecker(),
    ).validate(response.get_json())
    api.service.get_owned_events.assert_called_once_with(api.actors["owner"], 2, 3)


@pytest.mark.parametrize("target", ["events", "site_accounts"])
def test_owned_queries_require_auth_and_positive_pagination(api, target):
    path = f"/v1/users/me/{target}/owned"
    assert api.client.get(path).status_code == 401
    assert api.client.get(path + "?page=0", headers=authorization(api)).status_code == 422
    assert api.client.get(path + "?page_size=0", headers=authorization(api)).status_code == 422


@pytest.mark.parametrize("accepted", [False, True])
def test_event_invitation_routes(api, session, accepted):
    from sqlalchemy import text
    from app.repositories.storage.events.sql_event_repo import SqlEventRepo

    session.execute(text("INSERT INTO locations (place_id, details) VALUES ('venue', '{}')"))
    session.commit()
    SqlEventRepo(session).create_event(api.event)
    api.service.get_event_by_id.side_effect = SqlEventRepo(session).get_event_by_id
    assert api.client.get(f"/v1/event/{api.event.id}").json["collaborators"] == []
    path = "/v1/users/me/site_accounts/invites"
    assert api.client.get(path).status_code == 401
    assert api.client.get(path + "?page=0", headers=authorization(api, "collaborator")).status_code == 422
    assert api.client.get(path, headers=authorization(api)).json == []
    response = api.client.get(path, headers=authorization(api, "collaborator"))
    assert response.status_code == 200
    invite = response.json[0]
    assert invite["event_id"] == api.event.id
    assert invite["inviting"] == api.owner.id
    answer = f"/v1/site_accounts/answer/{invite['id']}"
    assert api.client.post(answer, json={"accepted": accepted}).status_code == 401
    assert api.client.post(answer, json={"accepted": accepted}, headers=authorization(api)).status_code == 404
    assert api.client.post(answer, json={"accepted": "true"}, headers=authorization(api, "collaborator")).status_code == 422
    assert api.client.post(answer, json={"accepted": accepted}, headers=authorization(api, "collaborator")).status_code == 200
    assert api.client.get(path, headers=authorization(api, "collaborator")).json == []
    assert api.client.post(answer, json={"accepted": accepted}, headers=authorization(api, "collaborator")).status_code == 404
    stored = SqlEventRepo(session).get_event_by_id(api.event.id)
    assert stored.accepted_collaborators == ([api.collaborator.id] if accepted else [])
    public = api.client.get(f"/v1/event/{api.event.id}")
    assert public.status_code == 200
    assert [site["collaborator-id"] for site in public.json["collaborators"]] == ([api.collaborator.id] if accepted else [])


@pytest.mark.parametrize("actor", ["collaborator", "moderator"])
def test_collaboration_query_and_leave_routes(api, session, actor):
    from sqlalchemy import text
    from app.database_models.events.event_model import event_collaborators
    from app.repositories.storage.events.sql_event_repo import SqlEventRepo

    api.collaborator.creator_id = api.actors[actor].id
    api.sites.update_site_account(api.collaborator)
    session.execute(text("INSERT INTO locations (place_id, details) VALUES ('venue', '{}')"))
    session.commit()
    repo = SqlEventRepo(session)
    repo.create_event(api.event)
    api.service.get_collaboration_events.side_effect = lambda user, page, size: repo.get_collaboration_events(user.id, page, size)
    api.service.leave_collaboration.side_effect = lambda user, event_id, site_id: repo.leave_collaboration(user.id, event_id, site_id)
    api.service.get_event_by_id.side_effect = repo.get_event_by_id
    path = "/v1/users/me/events/collaboration"
    assert api.client.get(path).status_code == 401
    assert api.client.get(path + "?page=0", headers=authorization(api, actor)).status_code == 422
    assert api.client.get(path + "?page_size=0", headers=authorization(api, actor)).status_code == 422
    assert api.client.get(path, headers=authorization(api, actor)).json == []
    session.execute(event_collaborators.update().values(accepted=True))
    session.commit()
    session.expire_all()
    response = api.client.get(path + "?page=1&page_size=1", headers=authorization(api, actor))
    assert response.status_code == 200
    assert [event["id"] for event in response.json] == [api.event.id]
    assert_schema(api, SimpleNamespace(get_json=lambda: response.json[0]), "EventObject")
    assert api.client.get(path + "?page=2&page_size=1", headers=authorization(api, actor)).json == []
    assert api.client.get(path, headers=authorization(api, "owner")).json == []
    result = api.client.delete(f"/v1/event/{api.event.id}?site_account={api.collaborator.id}", headers=authorization(api, actor))
    assert result.status_code == 200
    assert result.json == {"message": "Left collaboration."}
    api.service.remove_event.assert_not_called()
    assert repo.get_event_by_id(api.event.id).collaborators == []
    assert api.client.get(path, headers=authorization(api, actor)).json == []


@pytest.mark.parametrize("actor", ["owner", "stranger", "moderator"])
def test_leave_selector_never_deletes_event(api, actor):
    response = api.client.delete("/v1/event/123?site_account=999", headers=authorization(api, actor))
    assert response.status_code == 404
    api.service.leave_collaboration.assert_called_once_with(api.actors[actor], 123, 999)
    api.service.remove_event.assert_not_called()


def test_leave_selector_validates_integer(api):
    response = api.client.delete("/v1/event/123?site_account=invalid", headers=authorization(api))
    assert response.status_code == 422
    api.service.leave_collaboration.assert_not_called()
    api.service.remove_event.assert_not_called()
