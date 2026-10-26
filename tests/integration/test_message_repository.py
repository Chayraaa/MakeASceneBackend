from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.database_models.messages.message_model import MessageModel
from app.database_models.user_model import UserModel
from app.domain_models.messages.message import Message
from app.repositories.storage.messages.sql_message_repo import SqlMessageRepo


@pytest.fixture
def message_repo(session):
    session.add_all([UserModel(id=1, email="one@example.com", password="pw"),
                     UserModel(id=2, email="two@example.com", password="pw")])
    session.commit()
    return SqlMessageRepo(session)


def test_message_round_trip_update_and_delete(message_repo, session):
    sent = datetime(2026, 10, 26, 12, tzinfo=timezone.utc)
    assert message_repo.create_message(Message(user_id=1, title="Titel", message="Text", sent_at=sent))
    model = session.query(MessageModel).one()
    message = message_repo.get_message_by_id(model.id)
    assert message.id == model.id
    assert (message.user_id, message.title, message.message, message.read) == (1, "Titel", "Text", False)
    # SQLite drops timezone metadata; verify the stored timestamp components.
    assert message.sent_at.replace(tzinfo=timezone.utc) == sent
    message.title, message.message, message.read = "Neu", "Neuer Text", True
    assert message_repo.update_message(message)
    session.expire_all()
    updated = message_repo.get_message_by_id(message.id)
    assert (updated.title, updated.message, updated.read) == ("Neu", "Neuer Text", True)
    assert message_repo.delete_message(updated)
    assert message_repo.get_message_by_id(message.id) is None


def test_list_is_user_scoped_newest_first_and_paginated(message_repo):
    start = datetime(2026, 10, 26, tzinfo=timezone.utc)
    for index in range(5):
        assert message_repo.create_message(Message(user_id=1, title=str(index), message="body", sent_at=start + timedelta(minutes=index)))
    assert message_repo.create_message(Message(user_id=2, title="other", message="body", sent_at=start + timedelta(days=1)))
    assert [m.title for m in message_repo.get_messages_by_user_id(1, 1, 2)] == ["4", "3"]
    assert [m.title for m in message_repo.get_messages_by_user_id(1, 2, 2)] == ["2", "1"]
    assert [m.title for m in message_repo.get_messages_by_user_id(1, 3, 2)] == ["0"]
    assert message_repo.get_messages_by_user_id(1, 4, 2) == []
    assert message_repo.get_messages_by_user_id(999, 1, 2) == []


@pytest.mark.parametrize("method", ["update_message", "delete_message"])
def test_write_missing_message(message_repo, method):
    assert getattr(message_repo, method)(Message(id=999, user_id=1, title="x", message="y")) is False


@pytest.mark.parametrize("page,size", [(0, 1), (1, 0), (-1, 2), (2, -1)])
def test_invalid_pagination(page, size):
    session = Mock()
    with pytest.raises(ValueError):
        SqlMessageRepo(session).get_messages_by_user_id(1, page, size)
    session.query.assert_not_called()


@pytest.mark.parametrize("method,args,result,failure_point", [
    ("create_message", "message", False, "commit"),
    ("get_message_by_id", (1,), None, "get"),
    ("get_messages_by_user_id", (1, 1, 20), None, "query"),
    ("update_message", "message", False, "commit"),
    ("delete_message", "message", False, "commit"),
])
def test_database_errors_roll_back(method, args, result, failure_point):
    session = Mock()
    getattr(session, failure_point).side_effect = SQLAlchemyError("database failure")
    if args == "message":
        args = (Message(id=1, user_id=1, title="title", message="body"),)
    assert getattr(SqlMessageRepo(session), method)(*args) is result
    session.rollback.assert_called_once()
