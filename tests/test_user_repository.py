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