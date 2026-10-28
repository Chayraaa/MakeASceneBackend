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
    event_session.execute(event_collaborators.update().values(accepted=True))
    event_session.commit()
    event_session.expire_all()
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


def test_owned_events_filter_before_pagination(event_session, event_value):
    from dataclasses import replace

    user = UserModel(email="owner@example.com", password="hash")
    event_session.add(user)
    event_session.flush()
    event_session.get(SiteAccountModel, 1).creator_id = user.id
    event_session.commit()
    repo = SqlEventRepo(event_session)
    foreign = replace(event_value, id=None, owner_id=2, collaborators=[1])
    hidden = replace(event_value, id=None, name="Hidden", visible=False)
    public = replace(event_value, id=None, name="Public", visible=True)
    for value in (foreign, hidden, public):
        repo.create_event(value)
    assert [event.id for event in repo.get_owned_events(user.id)] == [hidden.id, public.id]
    assert [event.id for event in repo.get_owned_events(user.id, 2, 1)] == [public.id]
    assert repo.get_owned_events(user.id, 3, 1) == []
    assert repo.get_owned_events(999) == []


@pytest.mark.parametrize("accepted", [False, True])
def test_event_invitation_lifecycle(event_session, event_value, accepted):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo
    from app.domain_models.events.event_query import EventQuery

    recipient = UserModel(email="recipient@example.com", password="hash")
    other = UserModel(email="other@example.com", password="hash", role=2)
    event_session.add_all([recipient, other])
    event_session.flush()
    event_session.get(SiteAccountModel, 2).creator_id = recipient.id
    event_session.commit()
    events = SqlEventRepo(event_session)
    sites = SqlSiteAccountRepo(event_session)
    events.create_event(event_value)
    pending = sites.get_event_invites(recipient.id)
    assert len(pending) == 1
    invite = pending[0]
    assert invite == {"id": invite["id"], "event_id": event_value.id, "inviting": 1}
    assert sites.get_event_invites(other.id) == []
    assert not sites.answer_event_invite(other.id, invite["id"], True)
    assert events.get_event_by_id(event_value.id).accepted_collaborators == []
    assert events.query_events(EventQuery(collaborator_ids=[2]), 1, 25) == []
    assert sites.answer_event_invite(recipient.id, invite["id"], accepted)
    assert sites.get_event_invites(recipient.id) == []
    assert not sites.answer_event_invite(recipient.id, invite["id"], accepted)
    loaded = events.get_event_by_id(event_value.id)
    assert loaded.collaborators == ([2] if accepted else [])
    assert loaded.accepted_collaborators == ([2] if accepted else [])
    assert len(events.query_events(EventQuery(collaborator_ids=[2]), 1, 25)) == int(accepted)
    # Editing the event preserves accepted status, while re-inviting after rejection is pending.
    loaded.collaborators = [2]
    events.update_event(loaded)
    event_session.expire_all()
    assert events.get_event_by_id(event_value.id).accepted_collaborators == ([2] if accepted else [])
    assert len(sites.get_event_invites(recipient.id)) == int(not accepted)


def test_event_invites_paginate_pending_rows(event_session, event_value):
    from dataclasses import replace
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    user = UserModel(email="recipient@example.com", password="hash")
    event_session.add(user)
    event_session.flush()
    event_session.get(SiteAccountModel, 2).creator_id = user.id
    event_session.commit()
    events = SqlEventRepo(event_session)
    sites = SqlSiteAccountRepo(event_session)
    for index in range(3):
        events.create_event(replace(event_value, id=None, name=str(index)))
    first = sites.get_event_invites(user.id, 1, 1)[0]
    assert sites.answer_event_invite(user.id, first["id"], True)
    remaining = sites.get_event_invites(user.id)
    assert len(remaining) == 2
    assert sites.get_event_invites(user.id, 2, 1) == remaining[1:]
    assert sites.get_event_invites(user.id, 3, 1) == []


def test_invitation_migration_preserves_existing_collaborations(event_session, event_value):
    import importlib
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import text

    SqlEventRepo(event_session).create_event(event_value)
    connection = event_session.connection()
    connection.execute(text("DROP TABLE event_collaborators"))
    connection.execute(text(
        "CREATE TABLE event_collaborators ("
        "event_id INTEGER REFERENCES events(id) ON DELETE CASCADE, "
        "site_account_id INTEGER REFERENCES site_accounts(id) ON DELETE CASCADE, "
        "PRIMARY KEY (event_id, site_account_id))"
    ))
    connection.execute(text("INSERT INTO event_collaborators VALUES (:event, 2)"), {"event": event_value.id})
    migration = importlib.import_module("migrations.versions.e2f4a67b901c_event_collaborator_invitations")
    with Operations.context(MigrationContext.configure(connection)):
        migration.upgrade()
        rows = connection.execute(text("SELECT id, event_id, site_account_id, accepted FROM event_collaborators")).all()
        assert rows == [(1, event_value.id, 2, 1)]
        connection.execute(text("INSERT INTO event_collaborators (event_id, site_account_id) VALUES (:event, 1)"), {"event": event_value.id})
        assert connection.execute(text("SELECT id, accepted FROM event_collaborators WHERE site_account_id = 1")).one() == (2, 0)
        migration.downgrade()
        assert set(connection.execute(text("SELECT * FROM event_collaborators")).all()) == {(event_value.id, 1), (event_value.id, 2)}


def test_collaboration_events_and_leaving(event_session, event_value):
    from dataclasses import replace

    user = UserModel(email="collaborator@example.com", password="hash")
    event_session.add(user)
    event_session.flush()
    event_session.get(SiteAccountModel, 2).creator_id = user.id
    second = SiteAccountModel(name="second account", creator_id=user.id)
    foreign = SiteAccountModel(name="foreign account")
    event_session.add_all([second, foreign])
    event_session.commit()
    repo = SqlEventRepo(event_session)
    pending = replace(event_value, id=None, name="Pending")
    first = replace(event_value, id=None, name="First", visible=False, collaborators=[2, second.id, foreign.id])
    last = replace(event_value, id=None, name="Last")
    for event in (pending, first, last):
        repo.create_event(event)
    event_session.execute(event_collaborators.update().where(
        event_collaborators.c.event_id.in_([first.id, last.id])
    ).values(accepted=True))
    event_session.commit()
    event_session.expire_all()
    assert [event.id for event in repo.get_collaboration_events(user.id)] == [first.id, last.id]
    assert [event.id for event in repo.get_collaboration_events(user.id, 2, 1)] == [last.id]
    assert repo.get_collaboration_events(user.id, 3, 1) == []
    assert repo.get_collaboration_events(999) == []
    assert not repo.leave_collaboration(user.id, pending.id, 2)
    assert not repo.leave_collaboration(999, first.id, 2)
    assert repo.leave_collaboration(user.id, first.id, 2)
    assert not repo.leave_collaboration(user.id, first.id, 2)
    loaded = repo.get_event_by_id(first.id)
    assert loaded is not None
    assert loaded.accepted_collaborators == [second.id, foreign.id]
    assert loaded.collaborators == [second.id, foreign.id]
    assert repo.get_event_by_id(pending.id).collaborators == [2]
    assert [event.id for event in repo.get_collaboration_events(user.id)] == [first.id, last.id]
    assert not repo.leave_collaboration(user.id, first.id, foreign.id)
    assert repo.leave_collaboration(user.id, first.id, second.id)
    assert [event.id for event in repo.get_collaboration_events(user.id)] == [last.id]


@pytest.mark.parametrize("page,page_size", [(0, 25), (1, 0), (-1, 1)])
def test_collaboration_events_validate_pagination(event_session, page, page_size):
    with pytest.raises(ValueError):
        SqlEventRepo(event_session).get_collaboration_events(1, page, page_size)
