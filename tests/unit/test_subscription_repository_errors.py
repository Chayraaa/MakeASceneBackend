from unittest.mock import Mock

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.domain_models.subscriptions.event_subscription import EventSubscription
from app.domain_models.subscriptions.site_account_subscription import SiteAccountSubscription
from app.repositories.storage.subscriptions.sql_event_subscription_repo import SqlEventSubscriptionRepo
from app.repositories.storage.subscriptions.sql_site_account_subscription_repo import SqlSiteAccountSubscriptionRepo


@pytest.fixture(params=[("event", EventSubscription, SqlEventSubscriptionRepo),
                        ("site_account", SiteAccountSubscription, SqlSiteAccountSubscriptionRepo)])
def subscription_repo(request):
    kind, domain, repo_type = request.param
    session = Mock()
    return kind, domain(user_id=1, **{kind + "_id": 2}), repo_type(session), session


@pytest.mark.parametrize("operation", ["create", "update", "delete", "get_by_id", "get_by_user_id", "get_by_target", "get_by_pair"])
def test_database_errors_roll_back(subscription_repo, operation):
    kind, subscription, repo, session = subscription_repo
    method, args = operation, (subscription,)
    if operation == "get_by_target":
        method, args = f"get_by_{kind}_id", (2,)
    elif operation == "get_by_pair":
        method, args = f"get_by_user_and_{kind}_id", (1, 2)
    elif operation.startswith("get_by_"):
        args = (1,)
    failure_point = "commit" if operation in ("create", "update", "delete") else ("get" if operation == "get_by_id" else "query")
    getattr(session, failure_point).side_effect = SQLAlchemyError("database unavailable")
    expected = False if operation in ("create", "update", "delete") else None
    assert getattr(repo, method)(*args) is expected
    session.rollback.assert_called_once()
