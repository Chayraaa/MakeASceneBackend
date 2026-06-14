import pytest

from app.domain_models.tags.blocked_tag import BlockedTag


@pytest.fixture()
def user_and_tag(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="u@test.com", password="pw")
    user = user_repo.get_user_by_email("u@test.com")

    tag_repo = SqlTagRepo(session)
    tag_repo.create_tag("python")
    tag = tag_repo.get_tag_by_name("python")

    return user, tag


def test_create_blocked_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag

    success = repo.create(user, tag)
    blocked = repo.get_blocked_tag_by_user_and_tag(user, tag)

    assert success
    assert blocked is not None
    assert blocked.user_id == user.id
    assert blocked.tag_id == tag.id


def test_get_blocked_tags_by_user(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag

    tag_repo = SqlTagRepo(session)
    tag_repo.create_tag("django")
    tag2 = tag_repo.get_tag_by_name("django")

    repo.create(user, tag)
    repo.create(user, tag2)

    blocked_tags = repo.get_blocked_tags_by_user(user)
    assert len(blocked_tags) == 2
    assert all(bt.user_id == user.id for bt in blocked_tags)


def test_get_blocked_tags_by_user_empty(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    user, _ = user_and_tag

    blocked_tags = repo.get_blocked_tags_by_user(user)
    assert blocked_tags == []


def test_get_blocked_tags_by_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="u2@test.com", password="pw")
    user2 = user_repo.get_user_by_email("u2@test.com")

    repo.create(user, tag)
    repo.create(user2, tag)

    blocked_tags = repo.get_blocked_tags_by_tag(tag)
    assert len(blocked_tags) == 2
    assert all(bt.tag_id == tag.id for bt in blocked_tags)


def test_get_blocked_tag_by_id(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    blocked = repo.get_blocked_tag_by_user_and_tag(user, tag)

    result: BlockedTag | None = repo.get_blocked_tag_by_id(blocked.id)

    assert result is not None
    assert result.id == blocked.id
    assert result.user_id == user.id
    assert result.tag_id == tag.id


def test_get_blocked_tag_by_id_non_existing(session):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    assert repo.get_blocked_tag_by_id(999) is None


def test_get_blocked_tag_by_user_and_tag_non_existing(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag

    assert repo.get_blocked_tag_by_user_and_tag(user, tag) is None


def test_remove_blocked_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    blocked = repo.get_blocked_tag_by_user_and_tag(user, tag)

    success = repo.remove_blocked_tag(blocked)

    assert success
    assert repo.get_blocked_tag_by_id(blocked.id) is None


def test_remove_blocked_tag_non_existing(session):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    ghost = BlockedTag(id=999, user_id=1, tag_id=1)

    success = repo.remove_blocked_tag(ghost)
    assert not success


def test_update_blocked_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlBlockedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    blocked = repo.get_blocked_tag_by_user_and_tag(user, tag)

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="u2@test.com", password="pw")
    user2 = user_repo.get_user_by_email("u2@test.com")

    blocked.user_id = user2.id
    success = repo.update_blocked_tag(blocked)

    updated = repo.get_blocked_tag_by_id(blocked.id)
    assert success
    assert updated.user_id == user2.id


def test_update_blocked_tag_non_existing(session):
    from app.repositories.storage.tags.sql_blocked_tag_repo import SqlBlockedTagRepo

    repo = SqlBlockedTagRepo(session)
    ghost = BlockedTag(id=999, user_id=1, tag_id=1)

    success = repo.update_blocked_tag(ghost)
    assert not success