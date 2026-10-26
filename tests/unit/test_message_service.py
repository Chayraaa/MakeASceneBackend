from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain_models.messages.notify_message import NotifyMessage
from app.services.message_service import MessageService


@pytest.mark.parametrize("title,body", [("", "body"), ("title", ""), ("", "")])
def test_empty_notification_has_no_side_effects(title, body):
    repo, emails, users = Mock(), Mock(), Mock()
    service = MessageService(repo, emails, users)
    assert service.send_message(NotifyMessage(title, body), SimpleNamespace(id=1)) is False
    users.get_user.assert_not_called()
    repo.create_message.assert_not_called()
    emails.send_email.assert_not_called()


@pytest.mark.parametrize("user_exists,stored", [(False, True), (True, False)])
def test_send_failure_does_not_email(user_exists, stored):
    repo, emails, users = Mock(), Mock(), Mock()
    user = SimpleNamespace(id=1, email_preference=True)
    users.get_user.return_value = user if user_exists else None
    repo.create_message.return_value = stored
    service = MessageService(repo, emails, users)
    assert service.send_message(NotifyMessage("title", "body"), user) is False
    emails.send_email.assert_not_called()
    if not user_exists:
        repo.create_message.assert_not_called()


@pytest.mark.parametrize("page,size", [(0, 1), (1, 0), (-1, 20), (1, -2)])
def test_invalid_pagination_never_queries_repo(page, size):
    repo = Mock()
    service = MessageService(repo, Mock(), Mock())
    assert service.get_messages(SimpleNamespace(id=1), page, size) is None
    repo.get_messages_by_user_id.assert_not_called()


@pytest.mark.parametrize("result", [[], None, ["message"]])
def test_list_passes_user_and_pagination(result):
    repo = Mock()
    repo.get_messages_by_user_id.return_value = result
    service = MessageService(repo, Mock(), Mock())
    assert service.get_messages(SimpleNamespace(id=7), 2, 5) is result
    repo.get_messages_by_user_id.assert_called_once_with(7, 2, 5)
