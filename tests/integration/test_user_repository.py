from app.domain_models.user import User


def test_create_user(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo

    repo = SqlUserRepo(session)

    success = repo.create_user(email="test@test.com", password="password")
    user: User | None = repo.get_user_by_email("test@test.com")

    assert success
    assert user is not None
    assert user.id is not None
    assert user.email == "test@test.com"

def test_create_user_duplicate(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo
    repo = SqlUserRepo(session)

    assert repo.create_user(email="test@test.com", password="pw")
    assert not repo.create_user(email="test@test.com", password="pw2")

def test_get_non_existing_user(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo
    repo = SqlUserRepo(session)

    user = repo.get_user_by_email("no@user.com")
    assert user is None

def test_user_persistence(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo
    repo = SqlUserRepo(session)

    repo.create_user(email="a@b.com", password="pw")
    user: User | None = repo.get_user_by_email("a@b.com")

    assert user is not None
    assert user.email == "a@b.com"
    assert user.id is not None

def test_user_timezone_round_trip(session):
    from app.repositories.storage.sql_user_repo import SqlUserRepo
    repo = SqlUserRepo(session)
    assert repo.create_user(email="timezone@example.com", password="pw")
    user = repo.get_user_by_email("timezone@example.com")
    assert user.timezone == "UTC"
    user.timezone = "Europe/Berlin"
    assert repo.update_user(user)
    assert repo.get_user(user.id).timezone == "Europe/Berlin"
    assert repo.get_user_by_email(user.email).timezone == "Europe/Berlin"
