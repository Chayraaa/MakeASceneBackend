from types import SimpleNamespace
from unittest.mock import Mock, call

from app.services.site_account_service import SiteAccountService


def test_site_search_paginates_accessible_results_across_hidden_pages():
    accounts, search = Mock(), Mock()
    accounts.get_site_account_by_id.side_effect = lambda site_id: SimpleNamespace(
        id=site_id, visible=site_id >= 25, creator_id=10)
    search.search_by_semantic.side_effect = [
        [SimpleNamespace(id=i) for i in range(25)],
        [SimpleNamespace(id=i) for i in range(25, 50)],
        [SimpleNamespace(id=i) for i in range(50, 53)],
    ]
    service = SiteAccountService(accounts, Mock(), Mock(), search, Mock())
    found = service.query_site_accounts("Club", page=2)
    assert [item.id for item in found] == [50, 51, 52]
    assert search.search_by_semantic.call_args_list == [call("Club", 1), call("Club", 2), call("Club", 3)]


def test_site_owner_can_see_hidden_search_results_but_not_someone_elses():
    accounts, search = Mock(), Mock()
    accounts.get_site_account_by_id.side_effect = lambda site_id: SimpleNamespace(id=site_id, visible=False, creator_id=site_id)
    search.search_by_semantic.return_value = [SimpleNamespace(id=1), SimpleNamespace(id=2)]
    service = SiteAccountService(accounts, Mock(), Mock(), search, Mock())
    assert [item.id for item in service.query_site_accounts("Club", user=SimpleNamespace(id=1, role=0))] == [1]
