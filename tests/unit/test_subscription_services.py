from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.services.event_service import EventService
from app.services.site_account_service import SiteAccountService


@pytest.fixture(params=["event", "site_account"])
def subscription_service(request):
    kind = request.param
    targets, subscriptions = Mock(), Mock()
    if kind == "event":
        service = EventService(targets, Mock(), Mock(), subscription_repo=subscriptions)
    else:
        service = SiteAccountService(targets, Mock(), Mock(), Mock(), Mock(), subscription_repo=subscriptions)
    user = SimpleNamespace(id=1)
    return kind, service, targets, subscriptions, user


@pytest.mark.parametrize("exists,subscribed", [(False, False), (True, False), (True, True)])
def test_subscribe_checks_target_and_existing_subscription(subscription_service, exists, subscribed):
    kind, service, targets, repo, user = subscription_service
    getattr(targets, f"get_{kind}_by_id").return_value = object() if exists else None
    getattr(repo, f"get_by_user_and_{kind}_id").return_value = SimpleNamespace(user_id=1) if subscribed else None
    repo.create.return_value = True
    assert getattr(service, f"subscribe_to_{kind}")(user, 7) is (True if exists else None)
    if exists and not subscribed:
        created = repo.create.call_args.args[0]
        assert created.user_id == user.id
        assert getattr(created, f"{kind}_id") == 7
        assert created.notifications_enabled is False
    else:
        repo.create.assert_not_called()


@pytest.mark.parametrize("owner", [None, 1, 2])
@pytest.mark.parametrize("notify", [True, False])
def test_subscription_ownership_and_notifications(subscription_service, owner, notify):
    kind, service, _, repo, user = subscription_service
    subscription = SimpleNamespace(user_id=owner, notifications_enabled=not notify) if owner else None
    lookup = getattr(repo, f"get_by_user_and_{kind}_id")
    lookup.return_value = subscription
    repo.update.return_value = True
    repo.delete.return_value = True
    assert getattr(service, f"set_{kind}_notifications")(user, 7, notify) is (True if owner == 1 else None)
    assert getattr(service, f"unsubscribe_from_{kind}")(user, 7) is (True if owner == 1 else None)
    lookup.assert_called_with(1, 7)
    if owner == 1:
        assert subscription.notifications_enabled is notify
        repo.update.assert_called_once_with(subscription)
        repo.delete.assert_called_once_with(subscription)
    else:
        repo.update.assert_not_called()
        repo.delete.assert_not_called()


def test_subscription_list_scoped_and_paginated(subscription_service):
    kind, service, _, repo, user = subscription_service
    repo.get_by_user_id.return_value = []
    assert getattr(service, f"get_{kind}_subscriptions")(user, 2, 5) == []
    repo.get_by_user_id.assert_called_once_with(1, 2, 5)
    with pytest.raises(ValueError):
        getattr(service, f"get_{kind}_subscriptions")(user, 0, 5)
    with pytest.raises(ValueError):
        getattr(service, f"set_{kind}_notifications")(user, 7, "false")
