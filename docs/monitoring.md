# Monitoring

The provisioned Make A Scene dashboard (`makeascene-main`) keeps the existing
HTTP, authentication, user, tag, site account and email panels. Events and
locations appear immediately after HTTP traffic, followed by image storage.

`backend_operations_total{service,operation,result}` counts service calls.
`result` is `success`, `rejected` (a false/None return), `invalid` (ValueError),
or `error` (an unexpected exception). Empty query results are successful calls.
Event get misses are rejected calls, not infrastructure errors. Event update
rejections include both missing events and repository write failures.

`backend_operation_duration_seconds` includes failed calls and covers event
CRUD/query, location resolution/autocomplete, Geoapify, the Typesense location
cache and actual image uploads. HTTP image URLs bypass storage and are not
counted as uploads. Geoapify non-200 responses preserve the empty-result
fallback but count as errors. Network/JSON failures are counted and propagated.
Requests encode query parameters and have a 15-second network timeout.

`location_resolution_total{source}` distinguishes database hits, Place Details
geometry, autocomplete point fallbacks, and unresolved locations. This records
the chosen source before persistence; operation errors show persistence failures.
`event_query_results` records page sizes, including zero-result queries.
All labels use fixed values; queries, addresses, IDs and credentials are excluded.

Prometheus loads `prometheus/alerts.yml` in Compose and the same rules from its
Kubernetes ConfigMap. Alerts cover unreachable targets, repeated unexpected
operation errors (including Geoapify HTTP failures), rejected event writes and
unresolved locations. Invalid requests and individual read misses do not page.
Rules appear in Prometheus's Alerts page; notification delivery requires an
Alertmanager, which this repository does not configure.

Kubernetes uses a headless `backend-metrics` Service with DNS discovery to scrape
each backend pod separately. Scraping the load-balanced API Service mixes counters
from different pods and loses reliable rates. Compose retains its single backend
target. Deploy the updated Prometheus manifest together with the dashboard
ConfigMap using the existing Grafana provisioning process, then restart Prometheus
to load configuration and rule changes (its ConfigMap uses subPath mounts).

Validate configuration using:

```sh
docker run --rm --entrypoint promtool -v "$PWD/prometheus:/etc/prometheus:ro" prom/prometheus:latest check config /etc/prometheus/prometheus.yml
```

Run tests with `pytest --cov=app --cov-report=term-missing`. To include spatial
integration tests, set `POSTGIS_TEST_DATABASE_URI` to a disposable PostgreSQL
instance with PostGIS enabled. CI uses `postgis/postgis:18-3.6` and runs those tests.
Spatial tests isolate their tables in temporary schemas and roll back afterward.
