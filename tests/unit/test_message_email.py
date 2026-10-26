from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain_models.messages.notify_message import NotifyMessage
from app.services.message_service import MessageService


@pytest.mark.parametrize('email_preference', [True, False])
def test_message_email_uses_notification_content(email_preference):
    messages, emails, users = Mock(), Mock(), Mock()
    user = SimpleNamespace(id=1, email='user@example.com', email_preference=email_preference)
    users.get_user.return_value = user
    messages.create_message.return_value = True
    service = MessageService(messages, emails, users)
    notification = NotifyMessage(title='News & updates', body='Hello <friend>!\nYour next scene awaits.')

    assert service.send_message(notification, user) is True
    saved = messages.create_message.call_args.args[0]
    assert saved.title == notification.title
    assert saved.message == notification.body
    if email_preference:
        emails.send_email.assert_called_once()
        mail = emails.send_email.call_args.kwargs
        assert mail['subject'] == notification.title
        assert mail['recipient'] == user.email
        assert 'News &amp; updates' in mail['body']
        assert 'Hello &lt;friend&gt;!<br>Your next scene awaits.' in mail['body']
        assert 'href="#"' in mail['body']
        assert '{unsubscribe_url}' not in mail['body']
    else:
        emails.send_email.assert_not_called()
