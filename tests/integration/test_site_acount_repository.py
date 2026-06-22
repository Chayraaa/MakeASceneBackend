import pytest

from app.domain_models.site_account.SiteAccount import SiteAccount


@pytest.fixture()
def creator(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="creator@test.com", password="pw")
    return user_repo.get_user_by_email("creator@test.com")


def test_create_site_account(session, creator):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    success = repo.create_site_account(name="my-site", creator=creator)
    site_account = repo.get_site_account_by_name("my-site")

    assert success
    assert site_account is not None
    assert site_account.name == "my-site"
    assert site_account.creator_id == creator.id


def test_get_site_account_by_name_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    assert repo.get_site_account_by_name("missing-site") is None


def test_get_site_account_by_id(session, creator):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    repo.create_site_account(name="my-site", creator=creator)
    created = repo.get_site_account_by_name("my-site")

    result = repo.get_site_account_by_id(created.id)

    assert result is not None
    assert result.id == created.id
    assert result.name == "my-site"
    assert result.creator_id == creator.id


def test_get_site_account_by_id_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    assert repo.get_site_account_by_id(999) is None


def test_update_site_account(session, creator):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlSiteAccountRepo(session)
    repo.create_site_account(name="my-site", creator=creator)
    site_account = repo.get_site_account_by_name("my-site")

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="newcreator@test.com", password="pw")
    new_creator = user_repo.get_user_by_email("newcreator@test.com")

    site_account.name = "renamed-site"
    site_account.creator_id = new_creator.id
    site_account.layout = '{"theme": "dark"}'

    success = repo.update_site_account(site_account)
    updated = repo.get_site_account_by_id(site_account.id)

    assert success
    assert updated.name == "renamed-site"
    assert updated.creator_id == new_creator.id
    assert updated.layout == '{"theme": "dark"}'


def test_update_site_account_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    ghost = SiteAccount(id=999, name="ghost", creator_id=1, layout="{}")

    success = repo.update_site_account(ghost)
    assert not success


def test_remove_site_account(session, creator):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    repo.create_site_account(name="my-site", creator=creator)
    site_account = repo.get_site_account_by_name("my-site")

    success = repo.remove_site_account(site_account)

    assert success
    assert repo.get_site_account_by_id(site_account.id) is None


def test_remove_site_account_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_repo import SqlSiteAccountRepo

    repo = SqlSiteAccountRepo(session)
    ghost = SiteAccount(id=999, name="ghost", creator_id=1, layout="{}")

    success = repo.remove_site_account(ghost)
    assert not success