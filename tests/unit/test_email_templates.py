from datetime import datetime, timezone
from html import escape

import pytest

from app.domain_models.messages.message import Message
from app.domain_models.messages.notify_message import NotifyMessage
from app.email_templates import render_email_template
from app.services.auth_service import _assemble_password_reset_mail
from app.services.user_service import _assemble_mail


@pytest.mark.parametrize("assemble,path,subject", [
    (_assemble_mail, "/v1/auth/email/confirm?token=", "E-Mail-Adresse bestätigen"),
    (_assemble_password_reset_mail, "/v1/auth/password/reset?token=", "Passwort zurücksetzen"),
])
@pytest.mark.parametrize("base", [None, "https://example.com"])
def test_account_email_links_and_german_text(monkeypatch, assemble, path, subject, base):
    if base is None:
        monkeypatch.delenv("BASE_URL", raising=False)
    else:
        monkeypatch.setenv("BASE_URL", base)
    html = assemble("token&value")
    assert 'lang="de"' in html
    assert subject in html
    assert escape((base or "http://127.0.0.1:5000") + path + "token&value", quote=True) in html
    assert "{url}" not in html


def test_message_template_escapes_markup_and_preserves_all_newlines():
    html = render_email_template("user_message.html", title='<b>"Titel"</b>',
        message="<script>alert(1)</script>\r\nZeile 2\rZeile 3\n{title}", unsubscribe_url='https://example.com/?a=1&b="2"')
    assert '<script>' not in html
    assert '&lt;b&gt;&quot;Titel&quot;&lt;/b&gt;' in html
    assert '&lt;script&gt;alert(1)&lt;/script&gt;<br>Zeile 2<br>Zeile 3<br>{title}' in html
    assert 'https://example.com/?a=1&amp;b=&quot;2&quot;' in html
    assert "E-Mail-Benachrichtigungen abbestellen" in html


def test_message_defaults_and_serialization():
    before = datetime.now(timezone.utc)
    message = Message(user_id=9, title="Titel", message="Text")
    assert before <= message.sent_at <= datetime.now(timezone.utc)
    assert message.sent_at.tzinfo == timezone.utc
    assert message.to_dict() == dict(id=-1, title="Titel", message="Text", sent_at=message.sent_at.isoformat(), read=False)
    assert NotifyMessage("Titel", "Text").to_dict() == {"title": "Titel", "body": "Text"}
