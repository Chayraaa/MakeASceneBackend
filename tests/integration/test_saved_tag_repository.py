import pytest

from app.domain_models.tags.saved_tag import SavedTag


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


def test_create_saved_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag

    success = repo.create(user, tag)
    saved = repo.get_saved_tag_by_user_and_tag(user, tag)

    assert success
    assert saved is not None
    assert saved.user_id == user.id
    assert saved.tag_id == tag.id


def test_get_saved_tags_by_user(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag

    tag_repo = SqlTagRepo(session)
    tag_repo.create_tag("django")
    tag2 = tag_repo.get_tag_by_name("django")

    repo.create(user, tag)
    repo.create(user, tag2)

    saved_tags = repo.get_saved_tags_by_user(user)
    assert len(saved_tags) == 2
    assert all(st.user_id == user.id for st in saved_tags)


def test_get_saved_tags_by_user_empty(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    user, _ = user_and_tag

    saved_tags = repo.get_saved_tags_by_user(user)
    assert saved_tags == []


def test_get_saved_tags_by_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="u2@test.com", password="pw")
    user2 = user_repo.get_user_by_email("u2@test.com")

    repo.create(user, tag)
    repo.create(user2, tag)

    saved_tags = repo.get_saved_tags_by_tag(tag)
    assert len(saved_tags) == 2
    assert all(st.tag_id == tag.id for st in saved_tags)


def test_get_saved_tag_by_id(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    saved = repo.get_saved_tag_by_user_and_tag(user, tag)

    result: SavedTag | None = repo.get_saved_tag_by_id(saved.id)

    assert result is not None
    assert result.id == saved.id
    assert result.user_id == user.id
    assert result.tag_id == tag.id


def test_get_saved_tag_by_id_non_existing(session):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    assert repo.get_saved_tag_by_id(999) is None


def test_get_saved_tag_by_user_and_tag_non_existing(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag

    assert repo.get_saved_tag_by_user_and_tag(user, tag) is None


def test_remove_saved_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    saved = repo.get_saved_tag_by_user_and_tag(user, tag)

    success = repo.remove_saved_tag(saved)

    assert success
    assert repo.get_saved_tag_by_id(saved.id) is None


def test_remove_saved_tag_non_existing(session):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    ghost = SavedTag(id=999, user_id=1, tag_id=1)

    success = repo.remove_saved_tag(ghost)
    assert not success


def test_update_saved_tag(session, user_and_tag):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlSavedTagRepo(session)
    user, tag = user_and_tag
    repo.create(user, tag)
    saved = repo.get_saved_tag_by_user_and_tag(user, tag)

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="u2@test.com", password="pw")
    user2 = user_repo.get_user_by_email("u2@test.com")

    saved.user_id = user2.id
    success = repo.update_saved_tag(saved)

    updated = repo.get_saved_tag_by_id(saved.id)
    assert success
    assert updated.user_id == user2.id


def test_update_saved_tag_non_existing(session):
    from app.repositories.storage.tags.sql_saved_tag_repo import SqlSavedTagRepo

    repo = SqlSavedTagRepo(session)
    ghost = SavedTag(id=999, user_id=1, tag_id=1)

    success = repo.update_saved_tag(ghost)
    assert not success