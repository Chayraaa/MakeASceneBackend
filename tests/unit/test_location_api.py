from unittest.mock import Mock

import pytest
import requests

from app.metrics.operation_metrics import operations, duration
from app.repositories.external.location_repo import LocationRepo


@pytest.mark.parametrize('method,operation,payload,expected', [
    ('get_location_details', 'details', {'features': []}, {'features': []}),
    ('autocomplete_location', 'autocomplete', {'results': [{'place_id': 'p'}]}, [{'place_id': 'p'}]),
])
def test_geoapify_success(monkeypatch, method, operation, payload, expected):
    response = Mock(status_code=200)
    response.json.return_value = payload
    get = Mock(return_value=response)
    monkeypatch.setattr(requests, 'get', get)
    monkeypatch.setenv('GEOAPIFY_KEY', 'test-key')
    metric = operations.labels('geoapify', operation, 'success')
    before = metric._value.get()
    assert getattr(LocationRepo(), method)('Berlin & Potsdam') == expected
    params = get.call_args.kwargs
    assert params['timeout'] == 15
    assert params['params']['apiKey'] == 'test-key'
    assert 'Berlin & Potsdam' in params['params'].values()
    assert metric._value.get() == before + 1


@pytest.mark.parametrize('method,operation,empty', [
    ('get_location_details', 'details', {}), ('autocomplete_location', 'autocomplete', []),
])
def test_geoapify_http_error_is_monitored_without_logging_secret(monkeypatch, capsys, method, operation, empty):
    monkeypatch.setattr(requests, 'get', Mock(return_value=Mock(status_code=429)))
    metric = operations.labels('geoapify', operation, 'error')
    before = metric._value.get()
    assert getattr(LocationRepo(), method)('query') == empty
    assert metric._value.get() == before + 1
    assert capsys.readouterr().out == ''


@pytest.mark.parametrize('failure', [requests.Timeout('timeout'), ValueError('bad JSON')])
def test_geoapify_exception_counted_once_and_timed(monkeypatch, failure):
    response = Mock(status_code=200)
    response.json.side_effect = failure
    monkeypatch.setattr(requests, 'get', Mock(return_value=response))
    counter = operations.labels('geoapify', 'details', 'error')
    timer = duration.labels('geoapify', 'details')
    before = counter._value.get()
    total = timer._sum.get()
    with pytest.raises(type(failure)):
        LocationRepo().get_location_details('place')
    assert counter._value.get() == before + 1
    assert timer._sum.get() >= total
