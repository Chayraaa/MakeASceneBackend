from app.domain_models.tags.tag import Tag


def test_create_tag(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)

    success = repo.create_tag("python")
    tag: Tag | None = repo.get_tag_by_name("python")

    assert success
    assert tag is not None
    assert tag.id is not None
    assert tag.name == "python"


def test_create_tag_duplicate(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)

    assert repo.create_tag("python")
    assert not repo.create_tag("python")


def test_get_tag_by_name_non_existing(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)

    tag = repo.get_tag_by_name("nonexistent")
    assert tag is None


def test_get_tag_by_id(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)
    repo.create_tag("python")
    created = repo.get_tag_by_name("python")

    tag: Tag | None = repo.get_tag_by_id(created.id)

    assert tag is not None
    assert tag.id == created.id
    assert tag.name == "python"


def test_get_tag_by_id_non_existing(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)

    tag = repo.get_tag_by_id(999)
    assert tag is None


def test_update_tag(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)
    repo.create_tag("python")
    tag = repo.get_tag_by_name("python")

    tag.name = "django"
    success = repo.update_tag(tag)

    updated = repo.get_tag_by_id(tag.id)
    assert success
    assert updated is not None
    assert updated.name == "django"


def test_update_tag_non_existing(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)
    ghost = Tag(id=999, name="ghost")

    success = repo.update_tag(ghost)
    assert not success


def test_remove_tag(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)
    repo.create_tag("python")
    tag = repo.get_tag_by_name("python")

    success = repo.remove_tag(tag)

    assert success
    assert repo.get_tag_by_id(tag.id) is None


def test_remove_tag_non_existing(session):
    from app.repositories.storage.tags.sql_tag_repo import SqlTagRepo

    repo = SqlTagRepo(session)
    ghost = Tag(id=999, name="ghost")

    success = repo.remove_tag(ghost)
    assert not success