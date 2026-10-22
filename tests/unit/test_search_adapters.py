from unittest.mock import MagicMock

import pytest

from app.repositories.external.search_engine import typesense_location_search_repo as locations
from app.repositories.external.search_engine import typesense_site_account_search_repo as sites
from app.domain_models.site_account.SiteAccount import SiteAccount


@pytest.fixture(params=[locations, sites])
def search_repo(request, monkeypatch):
    module = request.param
    monkeypatch.setattr(module, '_initialized', False)
    client = MagicMock()
    repo_type = locations.TypesenseLocationSearchRepo if module is locations else sites.TypesenseSiteAccountSearchRepo
    return repo_type(client), client, module


def test_existing_collection_initialized_once(search_repo):
    repo, client, module = search_repo
    repo._ensure_ready()
    repo._ensure_ready()
    client.collections.__getitem__.return_value.retrieve.assert_called_once()
    client.collections.create.assert_not_called()


def test_missing_collection_is_created(search_repo):
    repo, client, module = search_repo
    client.collections.__getitem__.return_value.retrieve.side_effect = RuntimeError('not found')
    repo._ensure_ready()
    schema = client.collections.create.call_args.args[0]
    assert schema['name'] == ('locations' if module is locations else 'site_accounts')
    assert len(schema['fields']) >= 2


def test_location_document_mapping(monkeypatch):
    monkeypatch.setattr(locations, '_initialized', True)
    client = MagicMock()
    repo = locations.TypesenseLocationSearchRepo(client)
    value = repo.add_location({'place_id': 'p', 'formatted': 'Berlin', 'name': None, 'lat': 52,
                               'lon': 13, 'rank': {'importance': .9}, 'unused': 'discard'})
    assert value == {'id': 'p', 'formatted': 'Berlin', 'lat': 52, 'lon': 13, 'importance': .9}
    client.collections['locations'].documents.upsert.assert_called_once_with(value)
    client.collections['locations'].documents.search.return_value = {'hits': [{'document': value}]}
    assert repo.autocomplete_location('Berlin') == [value]
    params = client.collections['locations'].documents.search.call_args.args[0]
    assert params['q'] == 'Berlin' and params['per_page'] == 10


@pytest.mark.parametrize('operation', ['add_site_account', 'update_site_account', 'remove_site_account'])
def test_site_search_write(monkeypatch, operation):
    monkeypatch.setattr(sites, '_initialized', True)
    client = MagicMock()
    repo = sites.TypesenseSiteAccountSearchRepo(client)
    site = MagicMock(id=12, name='Artist')
    site.name = 'Artist'
    assert getattr(repo, operation)(site)
    if operation != 'remove_site_account':
        client.collections['site_accounts'].documents.upsert.assert_called_once_with({'id': '12', 'name': 'Artist'})


@pytest.mark.parametrize('operation', ['remove_site_account', 'search_by_semantic'])
def test_site_search_failures_are_safe(monkeypatch, operation):
    monkeypatch.setattr(sites, '_initialized', True)
    client = MagicMock()
    docs = client.collections['site_accounts'].documents
    docs.search.side_effect = RuntimeError('offline')
    docs.__getitem__.return_value.delete.side_effect = RuntimeError('offline')
    repo = sites.TypesenseSiteAccountSearchRepo(client)
    result = repo.remove_site_account(MagicMock(id=12)) if operation == 'remove_site_account' else repo.search_by_semantic('artist', 1)
    assert result == (False if operation == 'remove_site_account' else [])


def test_site_search_result_mapping(monkeypatch):
    monkeypatch.setattr(sites, '_initialized', True)
    client = MagicMock()
    client.collections['site_accounts'].documents.search.return_value = {'hits': [{'document': {'id': '12', 'name': 'Artist'}}]}
    result = sites.TypesenseSiteAccountSearchRepo(client).search_by_semantic('artist', 2)
    assert [(site.id, site.name) for site in result] == [(12, 'Artist')]
    assert client.collections['site_accounts'].documents.search.call_args.args[0]['page'] == 2
