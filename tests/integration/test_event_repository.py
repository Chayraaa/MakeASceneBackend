from app.database_models.subscriptions.event_subscription_model import EventSubscriptionModel
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event as sqlalchemy_event
from sqlalchemy.orm import Session

from app.database_models.events.event_model import EventModel, event_collaborators, event_tags
from app.database_models.site_account.site_account_model import SiteAccountModel
from app.database_models.tags.tag_model import TagModel
from app.database_models.user_model import UserModel
from app.domain_models.events.event import Event
from app.extensions import db
from app.repositories.storage.events.sql_event_repo import SqlEventRepo


@pytest.fixture
def event_session():
    engine = create_engine("sqlite:///:memory:")

    @sqlalchemy_event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.create_function("AsEWKB", 1, lambda value: value)

    # These tests exercise event storage without requiring the PostGIS extension.
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE locations (id INTEGER PRIMARY KEY, place_id VARCHAR UNIQUE, details VARCHAR, geometry BLOB)"
        )
        connection.exec_driver_sql("INSERT INTO locations (place_id, details) VALUES ('test-place', '{}')")
    db.metadata.create_all(engine, tables=[
        UserModel.__table__, SiteAccountModel.__table__, TagModel.__table__,
        EventModel.__table__, event_tags, event_collaborators, EventSubscriptionModel.__table__,
    ])
    with Session(engine) as session:
        session.add_all([
            SiteAccountModel(name="owner"), SiteAccountModel(name="collaborator"),
            TagModel(name="music"), TagModel(name="art"),
        ])
        session.commit()
        yield session
    engine.dispose()


@pytest.fixture
def event_value():
    return Event(
        name="Concert", description="Live music",
        from_=datetime(2026, 10, 22, 18, tzinfo=timezone.utc),
        till=datetime(2026, 10, 22, 20, tzinfo=timezone.utc),
        tags=[1, 1], place_id="test-place", layout=1,
        data=[{"text": "Original"}], owner_id=1, access=["public"],
        detail_data=[{"items": ["first"]}], collaborators=[2, 2], repeating="P1W",
    )


def test_event_crud_and_json_updates(event_session, event_value):
    repo = SqlEventRepo(event_session)
    assert repo.create_event(event_value)
    assert event_value.id is not None
    loaded = repo.get_event_by_id(event_value.id)
    assert loaded.tags == [1]
    assert loaded.collaborators == [2]
    assert loaded.owner_id == 1
    assert loaded.repeating == "P1W"
    assert loaded.data == event_value.data
    assert loaded.detail_data == event_value.detail_data
    assert loaded.access == ["public"]

    loaded.data[0]["text"] = "Updated"
    loaded.detail_data[0]["items"].append("second")
    loaded.access.append("members")
    loaded.tags = [2]
    loaded.collaborators = []
    loaded.owner_id = 2
    loaded.repeating = None
    assert repo.update_event(loaded)
    event_session.expire_all()
    updated = repo.get_event_by_id(loaded.id)
    assert updated.data == [{"text": "Updated"}]
    assert updated.detail_data == [{"items": ["first", "second"]}]
    assert updated.access == ["public", "members"]
    assert updated.tags == [2]
    assert updated.collaborators == []
    assert updated.owner_id == 2
    assert updated.repeating is None
    assert repo.remove_event(updated)
    assert repo.get_event_by_id(updated.id) is None
    assert event_session.execute(event_tags.select()).all() == []
    assert event_session.execute(event_collaborators.select()).all() == []


def test_missing_events(event_session, event_value):
    repo = SqlEventRepo(event_session)
    assert repo.get_event_by_id(999) is None
    assert not repo.update_event(event_value)
    assert not repo.remove_event(event_value)
    event_value.id = 999
    assert not repo.update_event(event_value)
    assert not repo.remove_event(event_value)


@pytest.mark.parametrize("organizers, collaborators, expected", [
    ([], [], ["first", "second", "third"]),
    ([1], [], ["first", "third"]),
    ([2], [], ["second"]),
    ([1, 2, 1], [], ["first", "second", "third"]),
    ([], [1], ["second"]),
    ([], [2], ["first"]),
    ([], [1, 2, 2], ["first", "second"]),
    ([1], [2], ["first"]),
    ([1], [1], []),
    ([999], [], []),
    ([], [999], []),
])
def test_query_organizers_and_collaborators(event_session, event_value, organizers, collaborators, expected):
    from dataclasses import replace
    from app.domain_models.events.event_query import EventQuery

    repo = SqlEventRepo(event_session)
    for name, owner, participants in [("first", 1, [2]), ("second", 2, [1]), ("third", 1, [])]:
        assert repo.create_event(replace(event_value, id=None, name=name, owner_id=owner, collaborators=participants))
    # No tag matches: fallback must still respect both site-account filters.
    query = EventQuery(
        organizer_ids=organizers, collaborator_ids=collaborators,
        included_tags=[999], include_partial=True,
    )
    results = repo.query_events(query, 1, 10)
    assert [event.name for event in results] == expected
    assert [event.name for event in repo.query_events(query, 1, 1)] == expected[:1]
    assert [event.name for event in repo.query_events(query, 2, 1)] == expected[1:2]


def test_unknown_relationship_does_not_change_event(event_session, event_value):
    repo = SqlEventRepo(event_session)
    repo.create_event(event_value)
    event_value.name = "Should not be saved"
    event_value.collaborators = [999]
    with pytest.raises(ValueError, match="Unknown SiteAccountModel IDs"):
        repo.update_event(event_value)
    event_session.commit()
    assert repo.get_event_by_id(event_value.id).name == "Concert"


def test_event_pagination(event_session, event_value):
    repo = SqlEventRepo(event_session)
    repo.create_event(event_value)
    first_id = event_value.id
    repo.create_event(event_value)
    assert [item.id for item in repo.get_events(1, 1)] == [first_id]
    assert [item.id for item in repo.get_events(2, 1)] == [event_value.id]
    assert repo.get_events(3, 1) == []
    with pytest.raises(ValueError):
        repo.get_events(0, 1)


def test_query_tag_ranking_or_exclusions_and_pagination(event_session, event_value):
    from copy import deepcopy
    from datetime import timedelta
    from app.domain_models.events.event_query import EventQuery

    repo = SqlEventRepo(event_session)
    values = []
    for tags, hours in [([1], 0), ([1, 2], 2), ([2], 1), ([], 0)]:
        value = deepcopy(event_value)
        value.tags = tags
        value.from_ += timedelta(hours=hours)
        value.till += timedelta(hours=hours)
        repo.create_event(value)
        values.append(value)
    query = EventQuery(included_tags=[1, 2])
    assert [event.id for event in repo.query_events(query, 1, 10)] == [
        values[1].id, values[2].id, values[0].id,
    ]
    assert [event.id for event in repo.query_events(query, 2, 1)] == [values[2].id]
    query.include_partial = True
    assert repo.query_events(query, 1, 10)[-1].id == values[3].id
    query.included_tags = [1]
    query.excluded_tags = [2]
    assert [event.id for event in repo.query_events(query, 1, 10)] == [values[0].id, values[3].id]


def test_query_time_overlap_and_literal_name(event_session, event_value):
    from datetime import timedelta
    from app.domain_models.events.event_query import EventQuery

    repo = SqlEventRepo(event_session)
    event_value.name = "100% Music"
    repo.create_event(event_value)
    query = EventQuery(name="100%", from_=event_value.from_ + timedelta(minutes=30), till=event_value.till)
    assert len(repo.query_events(query, 1, 10)) == 1
    query.name = "100_"
    assert repo.query_events(query, 1, 10) == []
    query.name = None
    query.from_ = event_value.till + timedelta(seconds=1)
    query.till = None
    assert repo.query_events(query, 1, 10) == []


def test_postgres_query_keeps_access_and_spatial_filters_with_fallback(event_session, monkeypatch):
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.orm import Query
    from app.domain_models.events.event_query import EventQuery

    statements = []

    def capture(query):
        statements.append(query.statement.compile(dialect=postgresql.dialect()))
        return []

    monkeypatch.setattr(Query, "all", capture)
    query = EventQuery(
        included_tags=[1], excluded_tags=[2], access=["wheelchair", "adults"], include_partial=True,
        place_id="city", longitude=13.4, latitude=52.5, radius_m=1000,
        geofence={"type": "Polygon", "coordinates": [[[13, 52], [14, 52], [14, 53], [13, 52]]]},
    )
    SqlEventRepo(event_session).query_events(query, 2, 10)
    sql = str(statements[0])
    assert "@>" in sql
    assert "ST_Intersects" in sql
    assert "ST_DWithin" in sql
    assert "geography" in sql.lower()
    assert "NOT (EXISTS" in sql
    assert "OFFSET" in sql and "LIMIT" in sql
    assert ["wheelchair", "adults"] in statements[0].params.values()


def test_visibility_persisted_and_hidden_events_excluded(event_session, event_value):
    from app.domain_models.events.event_query import EventQuery
    repo = SqlEventRepo(event_session)
    assert repo.create_event(event_value)
    assert repo.get_event_by_id(event_value.id).visible is True
    event_value.visible = False
    assert repo.update_event(event_value)
    assert repo.get_event_by_id(event_value.id).visible is False
    assert repo.query_events(EventQuery(), 1, 25) == []
    event_value.visible = True
    assert repo.update_event(event_value)
    assert len(repo.query_events(EventQuery(), 1, 25)) == 1


@pytest.mark.parametrize("role,owner,allowed", [(0, False, False), (0, True, True), (1, False, True), (2, False, True)])
def test_event_query_visibility_permissions_before_pagination(event_session, event_value, role, owner, allowed):
    from types import SimpleNamespace
    from dataclasses import replace
    from app.domain_models.events.event_query import EventQuery
    user = UserModel(email="viewer@example.com", password="pw", role=role)
    event_session.add(user)
    event_session.commit()
    account = event_session.get(SiteAccountModel, 1)
    if owner:
        account.creator_id = user.id
        event_session.commit()
    repo = SqlEventRepo(event_session)
    event_value.visible = False
    assert repo.create_event(event_value)
    public = replace(event_value, id=None, visible=True, name="Public")
    assert repo.create_event(public)
    viewer = SimpleNamespace(id=user.id, role=role)
    first = repo.query_events(EventQuery(), 1, 1, user=viewer)
    assert [item.name for item in first] == ([event_value.name] if allowed else ["Public"])
    second = repo.query_events(EventQuery(), 2, 1, user=viewer)
    assert [item.name for item in second] == (["Public"] if allowed else [])
