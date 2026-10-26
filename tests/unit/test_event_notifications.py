from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.domain_models.events.event import Event
from app.services.event_service import EventService
from app.services.site_account_service import SiteAccountService


@pytest.fixture
def setup():
    event = Event(name="Konzert", description="Alt", from_=datetime(2026, 10, 26, tzinfo=timezone.utc),
                  till=datetime(2026, 10, 27, tzinfo=timezone.utc), tags=[], place_id="place", layout=1,
                  data=[], detail_data=[], owner_id=3, access=[], id=7)
    repo, subscriptions, messages, users, sites = Mock(), Mock(), Mock(), Mock(), Mock()
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id)
    subscriptions.get_by_event_id.return_value = [
        SimpleNamespace(user_id=1, notifications_enabled=True),
        SimpleNamespace(user_id=2, notifications_enabled=False)]
    service = EventService(repo, Mock(), Mock(), subscriptions, messages, users, sites)
    service._prepare = deepcopy
    repo.get_event_by_id.return_value = event
    repo.create_event.return_value = repo.update_event.return_value = repo.remove_event.return_value = True
    return service, event, repo, subscriptions, messages, users, sites


@pytest.mark.parametrize("visible", [True, False])
def test_creation_publication(setup, visible):
    service, event, repo, _, messages, _, sites = setup
    event.visible = visible
    assert service.create_event(event)
    assert sites.notify_new_event.call_count == int(visible)
    messages.send_message.assert_not_called()
    repo.create_event.return_value = False
    sites.reset_mock()
    assert not service.create_event(event)
    sites.notify_new_event.assert_not_called()


@pytest.mark.parametrize("before,after", [(False, True), (True, False), (False, False), (True, True)])
def test_visibility_transitions(setup, before, after):
    service, event, _, _, messages, _, sites = setup
    event.visible = before
    assert service.update_event(replace(event, visible=after))
    assert sites.notify_new_event.call_count == int(not before and after)
    assert messages.send_message.call_count == int(before and not after)
    if before and not after:
        assert "abgesagt" in messages.send_message.call_args.args[0].body


def test_changed_fields_and_opt_out(setup):
    service, event, _, _, messages, _, sites = setup
    assert service.update_event(replace(event, description="Neu", name="Neuer Name"))
    messages.send_message.assert_called_once()
    notification, user = messages.send_message.call_args.args
    assert user.id == 1
    assert "Beschreibung: Alt → Neu" in notification.body
    assert "Name: Konzert → Neuer Name" in notification.body
    sites.notify_new_event.assert_not_called()


def test_failed_update_sends_nothing(setup):
    service, event, repo, _, messages, _, sites = setup
    repo.update_event.return_value = False
    assert not service.update_event(replace(event, description="Neu"))
    messages.send_message.assert_not_called()
    sites.notify_new_event.assert_not_called()


@pytest.mark.parametrize("visible,success", [(True, True), (True, False), (False, True)])
def test_delete_captures_recipients_before_cascade(setup, visible, success):
    service, event, repo, subscriptions, messages, _, _ = setup
    event.visible = visible
    def remove(value):
        subscriptions.get_by_event_id.return_value = []
        return success
    repo.remove_event.side_effect = remove
    assert service.remove_event(event) is success
    assert messages.send_message.call_count == int(visible and success)


def test_message_failure_does_not_fail_event_update(setup):
    service, event, _, subscriptions, messages, _, _ = setup
    subscriptions.get_by_event_id.return_value.append(SimpleNamespace(user_id=3, notifications_enabled=True))
    messages.send_message.side_effect = [RuntimeError("email unavailable"), True]
    assert service.update_event(replace(event, description="Neu"))
    assert messages.send_message.call_count == 2


def test_event_recipients_paginated(setup):
    service, event, _, subscriptions, messages, _, _ = setup
    subscriptions.get_by_event_id.side_effect = [
        [SimpleNamespace(user_id=i, notifications_enabled=True) for i in range(100)],
        [SimpleNamespace(user_id=100, notifications_enabled=True)]]
    assert service.update_event(replace(event, description="Neu"))
    assert messages.send_message.call_count == 101
    assert subscriptions.get_by_event_id.call_args.args == (7, 2, 100)


def test_site_followers_opt_in_and_pagination():
    accounts, users, subscriptions, messages = Mock(), Mock(), Mock(), Mock()
    accounts.get_site_account_by_id.return_value = SimpleNamespace(name="Club")
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id)
    subscriptions.get_by_site_account_id.side_effect = [
        [SimpleNamespace(user_id=i, notifications_enabled=i != 0) for i in range(100)],
        [SimpleNamespace(user_id=100, notifications_enabled=True)]]
    service = SiteAccountService(accounts, users, Mock(), Mock(), Mock(), subscriptions, messages)
    service.notify_new_event(SimpleNamespace(id=7, owner_id=3, name="Konzert"))
    assert messages.send_message.call_count == 100
    notification = messages.send_message.call_args.args[0]
    assert "Club" in notification.title
    assert "Konzert" in notification.body
    assert subscriptions.get_by_site_account_id.call_args.args == (3, 2, 100)


@pytest.mark.parametrize("field,value", [("tags", [1]), ("layout", 2)])
def test_tags_and_layout_do_not_notify(setup, field, value):
    service, event, _, _, messages, _, _ = setup
    assert service.update_event(replace(event, **{field: value}))
    messages.send_message.assert_not_called()


def test_content_changes_do_not_expose_data(setup):
    service, event, _, _, messages, _, _ = setup
    assert service.update_event(replace(event, data=[{"secret": "raw"}], detail_data=[{"text": "details"}]))
    body = messages.send_message.call_args.args[0].body
    assert body.count("Inhalte haben sich geändert.") == 1
    assert "secret" not in body and "details" not in body
    assert "Es gab Änderungen beim Event" in body


@pytest.mark.parametrize("month,expected", [(1, "19:00 CET"), (7, "20:00 CEST")])
def test_dates_use_recipient_timezone_with_dst(setup, month, expected):
    service, event, _, _, messages, users, _ = setup
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id, timezone="Europe/Berlin")
    start = datetime(2026, month, 10, 18, tzinfo=timezone.utc)
    assert service.update_event(replace(event, from_=start))
    body = messages.send_message.call_args.args[0].body
    assert expected in body
    assert f"10.{month:02d}.2026" in body


def test_location_changes_show_addresses(setup):
    service, event, _, _, messages, _, _ = setup
    service.location_service.get_location_data.side_effect = lambda place_id: SimpleNamespace(details={
        "formatted": "Alter Ort" if place_id == "place" else "Neuer Ort"})
    assert service.update_event(replace(event, place_id="new-id"))
    assert "Ort: Alter Ort → Neuer Ort" in messages.send_message.call_args.args[0].body


def test_location_coordinates_fallback(setup):
    service, event, _, _, messages, _, _ = setup
    service.location_service.get_location_data.return_value = SimpleNamespace(details='{"lat": 50.1, "lon": 11.2}')
    assert service.update_event(replace(event, place_id="new-id"))
    assert "50.1, 11.2" in messages.send_message.call_args.args[0].body


def test_each_recipient_gets_own_timezone(setup):
    service, event, _, subscriptions, messages, users, _ = setup
    subscriptions.get_by_event_id.return_value = [SimpleNamespace(user_id=i, notifications_enabled=True) for i in [1, 2]]
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id, timezone="Europe/Berlin" if user_id == 1 else "America/New_York")
    assert service.update_event(replace(event, from_=datetime(2026, 1, 10, 18, tzinfo=timezone.utc)))
    bodies = [call.args[0].body for call in messages.send_message.call_args_list]
    assert "19:00 CET" in bodies[0]
    assert "13:00 EST" in bodies[1]


@pytest.mark.parametrize("zone", ["Invalid/Zone", None, ""])
def test_invalid_recipient_timezone_falls_back_to_utc(setup, zone):
    service, event, _, _, messages, users, _ = setup
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id, timezone=zone)
    assert service.update_event(replace(event, from_=datetime(2026, 1, 10, 18, tzinfo=timezone.utc)))
    assert "10.01.2026 um 18:00 UTC" in messages.send_message.call_args.args[0].body


@pytest.mark.parametrize("field,before,after", [
    ("access", ["public", "wheelchair"], ["wheelchair", "public"]),
    ("collaborators", [1, 2], [2, 1]),
])
def test_reordered_sets_do_not_notify(setup, field, before, after):
    service, event, _, _, messages, _, _ = setup
    setattr(event, field, before)
    assert service.update_event(replace(event, **{field: after}))
    messages.send_message.assert_not_called()


def test_site_account_names_in_change_summary(setup):
    service, event, _, _, messages, _, sites = setup
    sites.get_site_account_by_id.side_effect = lambda site_id: SimpleNamespace(name=f"Club {site_id}")
    event.collaborators = [1]
    assert service.update_event(replace(event, owner_id=4, collaborators=[2]))
    body = messages.send_message.call_args.args[0].body
    assert "Veranstalter: Club 3 → Club 4" in body
    assert "Mitveranstalter: Club 1 → Club 2" in body


@pytest.mark.parametrize("details", [None, "not json", {}])
def test_unresolved_location_has_readable_fallback(setup, details):
    service, event, _, _, messages, _, _ = setup
    service.location_service.get_location_data.return_value = None if details is None else SimpleNamespace(details=details)
    assert service.update_event(replace(event, place_id="opaque-secret-id"))
    body = messages.send_message.call_args.args[0].body
    assert "Unbekannter Ort" in body
    assert "opaque-secret-id" not in body


def test_duplicate_and_deleted_recipients_are_skipped(setup):
    service, event, _, subscriptions, messages, users, _ = setup
    subscriptions.get_by_event_id.return_value = [SimpleNamespace(user_id=i, notifications_enabled=True) for i in [1, 1, 2]]
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=1) if user_id == 1 else None
    assert service.update_event(replace(event, name="Neu"))
    messages.send_message.assert_called_once()


@pytest.mark.parametrize("failure", [None, RuntimeError("storage unavailable")])
def test_subscription_read_failure_does_not_undo_update(setup, failure):
    service, event, _, subscriptions, messages, _, _ = setup
    subscriptions.get_by_event_id.return_value = None
    subscriptions.get_by_event_id.side_effect = failure
    assert service.update_event(replace(event, name="Neu"))
    messages.send_message.assert_not_called()


def test_site_notification_failure_does_not_block_other_followers():
    accounts, users, subscriptions, messages = Mock(), Mock(), Mock(), Mock()
    accounts.get_site_account_by_id.return_value = SimpleNamespace(name="Club")
    users.get_user.side_effect = lambda user_id: SimpleNamespace(id=user_id)
    subscriptions.get_by_site_account_id.return_value = [SimpleNamespace(user_id=i, notifications_enabled=True) for i in [1, 2]]
    messages.send_message.side_effect = [RuntimeError("email unavailable"), True]
    service = SiteAccountService(accounts, users, Mock(), Mock(), Mock(), subscriptions, messages)
    service.notify_new_event(SimpleNamespace(id=7, owner_id=3, name="Konzert"))
    assert messages.send_message.call_count == 2


def test_publication_delivery_error_does_not_fail_creation(setup):
    service, event, _, _, _, _, sites = setup
    sites.notify_new_event.side_effect = RuntimeError("notification service unavailable")
    assert service.create_event(event)


def test_missing_event_cannot_be_deleted(setup):
    service, event, repo, _, messages, _, _ = setup
    repo.get_event_by_id.return_value = None
    assert service.remove_event(event) is False
    repo.remove_event.assert_not_called()
    messages.send_message.assert_not_called()


def test_unsent_message_is_logged_without_failing_update(setup, caplog):
    service, event, _, _, messages, _, _ = setup
    messages.send_message.return_value = False
    assert service.update_event(replace(event, name="Neu"))
    assert "Failed to notify user" in caplog.text


@pytest.mark.parametrize("scenario", ["missing_account", "failed_lookup", "raised_lookup", "failed_delivery"])
def test_site_notification_failures_are_logged_or_skipped(scenario, caplog):
    accounts, users, subscriptions, messages = Mock(), Mock(), Mock(), Mock()
    accounts.get_site_account_by_id.return_value = SimpleNamespace(name="Club")
    users.get_user.return_value = SimpleNamespace(id=1)
    subscriptions.get_by_site_account_id.return_value = [SimpleNamespace(user_id=1, notifications_enabled=True)]
    if scenario == "missing_account":
        accounts.get_site_account_by_id.return_value = None
    elif scenario == "failed_lookup":
        subscriptions.get_by_site_account_id.return_value = None
    elif scenario == "raised_lookup":
        subscriptions.get_by_site_account_id.side_effect = RuntimeError("database unavailable")
    else:
        messages.send_message.return_value = False
    service = SiteAccountService(accounts, users, Mock(), Mock(), Mock(), subscriptions, messages)
    service.notify_new_event(SimpleNamespace(id=7, owner_id=3, name="Konzert"))
    if scenario == "failed_delivery":
        messages.send_message.assert_called_once()
    else:
        messages.send_message.assert_not_called()
    if scenario != "missing_account":
        assert "notification" in caplog.text.lower() or "notify" in caplog.text.lower()
