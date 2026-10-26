import pytest
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database_models.subscriptions.event_subscription_model import EventSubscriptionModel
from app.database_models.subscriptions.site_account_subscription_model import SiteAccountSubscriptionModel


@pytest.fixture(params=[(EventSubscriptionModel, "event_id", "events"),
                        (SiteAccountSubscriptionModel, "site_account_id", "site_accounts")])
def subscription_db(request):
    model, target_key, target_table = request.param
    engine = create_engine("sqlite://")
    metadata = MetaData()
    users = Table("users", metadata, Column("id", Integer, primary_key=True))
    targets = Table(target_table, metadata, Column("id", Integer, primary_key=True))
    model.__table__.to_metadata(metadata)
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=ON"))
        metadata.create_all(connection)
        connection.execute(insert(users).values(id=1))
        connection.execute(insert(targets).values(id=2))
        connection.commit()
    with Session(engine) as session:
        yield session, model, target_key, target_table
    engine.dispose()


def test_defaults_relationships_and_notification_toggle(subscription_db):
    session, model, key, _ = subscription_db
    subscription = model(user_id=1, **{key: 2})
    session.add(subscription)
    session.commit()
    assert subscription.id is not None
    assert subscription.notifications_enabled is False
    subscription.notifications_enabled = True
    session.commit()
    session.expire_all()
    assert session.get(model, subscription.id).notifications_enabled is True
    assert model.user.property.back_populates


def test_duplicate_subscription_rejected(subscription_db):
    session, model, key, _ = subscription_db
    session.add(model(user_id=1, **{key: 2}))
    session.commit()
    session.add(model(user_id=1, **{key: 2}))
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()


@pytest.mark.parametrize("parent", ["users", "target"])
def test_parent_deletion_removes_subscriptions(subscription_db, parent):
    session, model, key, target = subscription_db
    session.add(model(user_id=1, **{key: 2}))
    session.commit()
    table = "users" if parent == "users" else target
    session.execute(text(f"DELETE FROM {table}"))
    session.commit()
    assert session.scalars(select(model)).all() == []


def test_database_default_without_orm(subscription_db):
    session, model, key, _ = subscription_db
    session.execute(text(f"INSERT INTO {model.__tablename__} (user_id, {key}) VALUES (1, 2)"))
    session.commit()
    assert session.scalars(select(model)).one().notifications_enabled is False


def test_subscription_repository_crud(subscription_db):
    from app.domain_models.subscriptions.event_subscription import EventSubscription
    from app.domain_models.subscriptions.site_account_subscription import SiteAccountSubscription
    from app.repositories.storage.subscriptions.sql_event_subscription_repo import SqlEventSubscriptionRepo
    from app.repositories.storage.subscriptions.sql_site_account_subscription_repo import SqlSiteAccountSubscriptionRepo

    session, model, key, _ = subscription_db
    domain, repo_type = ((EventSubscription, SqlEventSubscriptionRepo) if key == "event_id"
                        else (SiteAccountSubscription, SqlSiteAccountSubscriptionRepo))
    repo = repo_type(session)
    subscription = domain(user_id=1, **{key: 2})
    assert subscription.id == -1
    assert subscription.notifications_enabled is False
    assert repo.create(subscription)
    assert subscription.id > 0
    assert repo.get_by_id(subscription.id) == subscription
    assert repo.get_by_user_id(1) == [subscription]
    assert getattr(repo, f"get_by_{key}")(2) == [subscription]
    assert repo.get_by_user_id(999) == []
    assert getattr(repo, f"get_by_{key}")(999) == []
    assert repo.get_by_id(999) is None
    assert not repo.update(domain(id=999, user_id=1, **{key: 2}))
    assert not repo.delete(domain(id=999, user_id=1, **{key: 2}))
    subscription.notifications_enabled = True
    assert repo.update(subscription)
    assert repo.get_by_id(subscription.id).notifications_enabled is True
    assert subscription.to_dict() == {"id": subscription.id, "user_id": 1, key: 2, "notifications_enabled": True}
    assert not repo.create(domain(user_id=1, **{key: 2}))
    assert repo.get_by_id(subscription.id) is not None
    assert repo.delete(subscription)
    assert repo.get_by_id(subscription.id) is None


@pytest.mark.parametrize("by_user", [True, False])
def test_subscription_list_pagination(subscription_db, by_user):
    from app.repositories.storage.subscriptions.sql_event_subscription_repo import SqlEventSubscriptionRepo
    from app.repositories.storage.subscriptions.sql_site_account_subscription_repo import SqlSiteAccountSubscriptionRepo

    session, model, key, target = subscription_db
    repo = (SqlEventSubscriptionRepo if key == "event_id" else SqlSiteAccountSubscriptionRepo)(session)
    parent = target if by_user else "users"
    for number in range(3, 8):
        session.execute(text(f"INSERT INTO {parent} (id) VALUES (:id)"), {"id": number})
        session.add(model(user_id=1 if by_user else number, **{key: number if by_user else 2}))
    # Include a subscription outside the selected user/target.
    session.execute(text("INSERT INTO users (id) VALUES (99)"))
    session.execute(text(f"INSERT INTO {target} (id) VALUES (99)"))
    session.add(model(user_id=99, **{key: 99}))
    session.commit()
    method = repo.get_by_user_id if by_user else getattr(repo, f"get_by_{key}")
    value = 1 if by_user else 2
    expected = [row.id for row in session.scalars(select(model).where(
        model.user_id == 1 if by_user else getattr(model, key) == 2
    ).order_by(model.id))]
    assert len(expected) == 5
    assert [s.id for s in method(value, page=1, page_size=2)] == expected[:2]
    assert [s.id for s in method(value, page=2, page_size=2)] == expected[2:4]
    assert [s.id for s in method(value, page=3, page_size=2)] == expected[4:]
    assert method(value, page=4, page_size=2) == []
    for page, size in [(0, 2), (-1, 2), (1, 0), (1, -1)]:
        with pytest.raises(ValueError, match="positive"):
            method(value, page=page, page_size=size)


def test_subscription_pair_lookup_is_scoped_to_user_and_target(subscription_db):
    from app.repositories.storage.subscriptions.sql_event_subscription_repo import SqlEventSubscriptionRepo
    from app.repositories.storage.subscriptions.sql_site_account_subscription_repo import SqlSiteAccountSubscriptionRepo
    session, model, key, _ = subscription_db
    repo = (SqlEventSubscriptionRepo if key == "event_id" else SqlSiteAccountSubscriptionRepo)(session)
    session.add(model(user_id=1, **{key: 2}))
    session.commit()
    lookup = getattr(repo, "get_by_user_and_" + key)
    found = lookup(1, 2)
    assert found.user_id == 1 and getattr(found, key) == 2
    assert lookup(999, 2) is None
    assert lookup(1, 999) is None
