"""Bounded service labels: never include queries, IDs, URLs or exception messages."""
from functools import wraps

from prometheus_client import Counter, Histogram


operations = Counter(
    "backend_operations_total", "Service operations by outcome (success, rejected, invalid, error).",
    ["service", "operation", "result"],
)
duration = Histogram(
    "backend_operation_duration_seconds", "Service latency including failed operations.",
    ["service", "operation"], buckets=(.005, .025, .1, .25, .5, 1, 2.5, 5, 10, 30, 60),
)
results = Histogram(
    "event_query_results", "Number of events returned per query page.",
    buckets=(0, 1, 5, 10, 25, 50, 100),
)
location_sources = Counter(
    "location_resolution_total", "Location resolution source; unresolved means no usable geometry.",
    ["source"],
)


def monitored(service, operation):
    def decorate(function):
        @wraps(function)
        def wrapped(*args, **kwargs):
            with duration.labels(service, operation).time():
                try:
                    value = function(*args, **kwargs)
                except ValueError:
                    operations.labels(service, operation, "invalid").inc()
                    raise
                except Exception:
                    operations.labels(service, operation, "error").inc()
                    raise
                operations.labels(service, operation, "rejected" if value is False or value is None else "success").inc()
                if service == "event" and operation == "query":
                    results.observe(len(value))
                return value
        return wrapped
    return decorate
