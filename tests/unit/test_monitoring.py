import json
from pathlib import Path

import pytest
import yaml
from prometheus_client import CollectorRegistry, generate_latest, multiprocess

from app.metrics.operation_metrics import monitored, operations

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize('value,outcome', [(True, 'success'), (False, 'rejected'), (None, 'rejected'), ([], 'success')])
def test_operation_outcomes(value, outcome):
    counter = operations.labels('test', 'return', outcome)
    before = counter._value.get()
    wrapped = monitored('test', 'return')(lambda: value)
    assert wrapped() is value
    assert counter._value.get() == before + 1


@pytest.mark.parametrize('failure,outcome', [(ValueError('invalid'), 'invalid'), (RuntimeError('failure'), 'error')])
def test_operation_exceptions_propagate(failure, outcome):
    def fail():
        raise failure
    counter = operations.labels('test', 'raise', outcome)
    before = counter._value.get()
    with pytest.raises(type(failure)):
        monitored('test', 'raise')(fail)()
    assert counter._value.get() == before + 1


def test_metrics_are_available_to_multiprocess_scraper():
    operations.labels('event', 'query', 'success').inc()
    registry = CollectorRegistry()
    multiprocess.MultiProcessCollector(registry)
    output = generate_latest(registry).decode()
    assert 'backend_operations_total{operation="query",result="success",service="event"}' in output


def test_prometheus_rules_are_provisioned_for_compose_and_kubernetes():
    rules = yaml.safe_load((ROOT / 'prometheus/alerts.yml').read_text())
    config = yaml.safe_load((ROOT / 'prometheus/prometheus.yml').read_text())
    assert '/etc/prometheus/alerts.yml' in config['rule_files']
    documents = list(yaml.safe_load_all((ROOT / 'k8s/05-prometheus.yaml').read_text()))
    assert yaml.safe_load(documents[0]['data']['alerts.yml']) == rules
    kube_config = yaml.safe_load(documents[0]['data']['prometheus.yml'])
    assert kube_config['rule_files'] == config['rule_files']
    discovery = kube_config['scrape_configs'][0]['dns_sd_configs'][0]
    assert discovery['names'] == ['backend-metrics.makeascene.svc.cluster.local']
    service = documents[-1]
    assert service['metadata']['name'] == 'backend-metrics'
    assert service['spec']['clusterIP'] == 'None'
    assert service['spec']['selector'] == {'app': 'backend'}
    mounts = documents[1]['spec']['template']['spec']['containers'][0]['volumeMounts']
    assert any(m['mountPath'] == '/etc/prometheus/alerts.yml' for m in mounts)
    compose = yaml.safe_load((ROOT / 'docker-compose.yaml').read_text())
    assert './prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro' in compose['services']['prometheus']['volumes']


def test_dashboard_panels_have_unique_ids_and_do_not_overlap():
    dashboard = json.loads((ROOT / 'grafana/dashboards/makeascene.json').read_text(encoding='utf-8'))
    manifests = yaml.safe_load_all((ROOT / 'k8s/12-grafana.yaml').read_text(encoding='utf-8'))
    embedded = next(doc for doc in manifests if doc['metadata']['name'] == 'grafana-dashboard-makeascene')
    assert json.loads(embedded['data']['makeascene.json']) == dashboard
    panels = dashboard['panels']
    assert len({p['id'] for p in panels}) == len(panels)
    for index, panel in enumerate(panels):
        a = panel['gridPos']
        for other in panels[index + 1:]:
            b = other['gridPos']
            assert not (a['x'] < b['x'] + b['w'] and b['x'] < a['x'] + a['w'] and
                        a['y'] < b['y'] + b['h'] and b['y'] < a['y'] + a['h']), (panel['title'], other['title'])
    expressions = ' '.join(t.get('expr', '') for p in panels for t in p.get('targets', []))
    for metric in ('backend_operations_total', 'backend_operation_duration_seconds_bucket',
                   'location_resolution_total', 'event_query_results_bucket'):
        assert metric in expressions
