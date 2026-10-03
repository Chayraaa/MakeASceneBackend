from prometheus_client import Counter, Histogram

site_account_created = Counter(
    'site_account_created_total',
    'Number of site account creation attempts. Tracks both DB write and Typesense sync steps; '
    'a success=false result means at least one of those steps failed.',
    ['success']
)

site_account_deleted = Counter(
    'site_account_deleted_total',
    'Number of site account deletion attempts. '
    'Deletion requires both a DB removal and a Typesense document delete; '
    'success=false means the DB removal failed (Typesense is not attempted in that case).',
    ['success']
)

site_account_application_submitted = Counter(
    'site_account_application_submitted_total',
    'Number of artist site-account applications submitted. '
    'This is the entry point of the artist onboarding funnel.'
)

site_account_application_deleted = Counter(
    'site_account_application_deleted_total',
    'Number of site-account applications deleted. '
    'Combined with submitted total, gives an approximation of the review throughput.'
)

site_account_images_uploaded = Counter(
    'site_account_images_uploaded_total',
    'Number of individual base64 images extracted from layout JSON and saved to object storage. '
    'Each image triggers one S3 write; high values indicate cost pressure on the storage backend.'
)

site_account_search_errors = Counter(
    'site_account_search_errors_total',
    'Number of Typesense search failures when querying site accounts. '
    'Failures are silently swallowed and return an empty list, so without this counter '
    'a degraded or down Typesense is indistinguishable from "no results found".'
)

site_account_typesense_sync_errors = Counter(
    'site_account_typesense_sync_errors_total',
    'Number of Typesense document sync failures broken down by operation type. '
    'The "remove" operation catches its own exceptions; "add" and "update" will propagate. '
    "Labels: operation ('add', 'update', 'remove').",
    ['operation']
)

site_account_search_duration = Histogram(
    'site_account_search_duration_seconds',
    'End-to-end duration of a site account search: one Typesense query followed by one DB '
    'lookup per result (N+1 pattern). Latency grows linearly with the number of hits returned.'
)

site_account_image_processing_duration = Histogram(
    'site_account_image_processing_duration_seconds',
    'Duration of the recursive _replace_images pass over a layout update. '
    'This walk is proportional to the size and nesting depth of the layout JSON, '
    'and each base64 image found triggers a synchronous S3 write.'
)

site_account_layout_image_count = Histogram(
    'site_account_layout_image_count',
    'Number of base64 images found and replaced per layout update. '
    'Use this to understand the P95 image density per modify call and to size object storage load.',
    buckets=[0, 1, 2, 5, 10, 20, 50]
)
