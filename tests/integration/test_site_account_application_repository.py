import pytest

from app.domain_models.site_account.SiteAccountApplication import SiteAccountApplication


@pytest.fixture()
def requestor(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="requestor@test.com", password="pw")
    return user_repo.get_user_by_email("requestor@test.com")


def _create_application(session, repo, requestor, **overrides):
    """Creates an application via the repo and returns its id.

    create_application() only returns a bool, so we look the row up
    directly through the session to get the generated id back.
    """
    from app.database_models.site_account.site_account_application_model import SiteAccountApplicationModel

    defaults = dict(
        artist_name="artist",
        account_name="my-account",
        reason="because",
        sources=["instagram.com/artist", "twitter.com/artist"],
        contacts=["artist@email.com"],
    )
    defaults.update(overrides)

    repo.create_application(requestor=requestor, **defaults)

    return session.query(SiteAccountApplicationModel).filter_by(account_name=defaults["account_name"]).first().id


def test_create_application(session, requestor):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    application_id = _create_application(session, repo, requestor)

    result = repo.get_application_by_id(application_id)

    assert result is not None
    assert result.requestor_id == requestor.id
    assert result.artist_name == "artist"
    assert result.account_name == "my-account"
    assert result.reason == "because"
    assert sorted(result.sources) == sorted(["instagram.com/artist", "twitter.com/artist"])
    assert sorted(result.contacts) == ["artist@email.com"]


def test_create_application_no_sources_or_contacts(session, requestor):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    application_id = _create_application(session, repo, requestor, sources=[], contacts=[])

    result = repo.get_application_by_id(application_id)

    assert result is not None
    assert result.sources == []
    assert result.contacts == []


def test_get_application_by_id_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    assert repo.get_application_by_id(999) is None


def test_get_applications_pagination(session, requestor):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    for i in range(3):
        _create_application(session, repo, requestor, account_name=f"account-{i}")

    first_page = repo.get_applications(page=1, page_size=2)
    second_page = repo.get_applications(page=2, page_size=2)

    assert len(first_page) == 2
    assert len(second_page) == 1
    assert all(isinstance(a, SiteAccountApplication) for a in first_page + second_page)
    # no overlap between pages
    first_page_ids = {a.id for a in first_page}
    second_page_ids = {a.id for a in second_page}
    assert first_page_ids.isdisjoint(second_page_ids)


def test_get_applications_empty(session):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    assert repo.get_applications(page=1, page_size=10) == []


def test_update_application(session, requestor):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlSiteAccountApplicationRepo(session)
    application_id = _create_application(session, repo, requestor)
    application = repo.get_application_by_id(application_id)

    user_repo = SqlUserRepo(session)
    user_repo.create_user(email="newrequestor@test.com", password="pw")
    new_requestor = user_repo.get_user_by_email("newrequestor@test.com")

    application.requestor_id = new_requestor.id
    application.artist_name = "renamed-artist"
    application.account_name = "renamed-account"
    application.reason = "updated reason"
    application.sources = ["onlyfans.com/artist"]
    application.contacts = ["new@email.com", "second@email.com"]

    success = repo.update_application(application)
    updated = repo.get_application_by_id(application_id)

    assert success
    assert updated.requestor_id == new_requestor.id
    assert updated.artist_name == "renamed-artist"
    assert updated.account_name == "renamed-account"
    assert updated.reason == "updated reason"
    assert updated.sources == ["onlyfans.com/artist"]
    assert sorted(updated.contacts) == sorted(["new@email.com", "second@email.com"])


def test_update_application_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    ghost = SiteAccountApplication(id=999, requestor_id=1, artist_name="ghost", account_name="ghost-account",
                                   reason="ghost", sources=[], contacts=[])

    success = repo.update_application(ghost)
    assert not success


def test_delete_application(session, requestor):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    application_id = _create_application(session, repo, requestor)
    application = repo.get_application_by_id(application_id)

    success = repo.delete_application(application)

    assert success
    assert repo.get_application_by_id(application_id) is None


def test_delete_application_non_existing(session):
    from app.repositories.storage.site_account.sql_site_account_application_repo import SqlSiteAccountApplicationRepo

    repo = SqlSiteAccountApplicationRepo(session)
    ghost = SiteAccountApplication(id=999, requestor_id=1, artist_name="ghost", account_name="ghost-account",
                                   reason="ghost", sources=[], contacts=[])

    assert repo.delete_application(ghost) is False