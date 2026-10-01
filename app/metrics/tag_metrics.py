from prometheus_client import Counter, Histogram

tag_created = Counter(
    'tag_created_total',
    'Number of tag creation attempts. '
    "Labels: success ('true', 'false'). "
    'Creation writes to the DB then enqueues a background LLM expansion job; '
    'success=false means the DB write failed.',
    ['success']
)

tag_deleted = Counter(
    'tag_deleted_total',
    'Number of tag deletion attempts. '
    "Labels: success ('true', 'false'). "
    'Deletion removes from Typesense then from the DB.',
    ['success']
)

tag_saved = Counter(
    'tag_saved_total',
    'Number of tag save operations by users. '
    "Labels: success ('true', 'false'). "
    'A user engagement signal; success=false means the tag ID does not exist.',
    ['success']
)

tag_blocked = Counter(
    'tag_blocked_total',
    'Number of tag block operations by users. '
    "Labels: success ('true', 'false'). "
    'A content preference signal; success=false means the tag ID does not exist.',
    ['success']
)

tag_unsaved = Counter(
    'tag_unsaved_total',
    'Number of tag unsave operations. '
    'Combined with saved total, gives a net-save rate per user cohort.'
)

tag_unblocked = Counter(
    'tag_unblocked_total',
    'Number of tag unblock operations.'
)

tag_search_errors = Counter(
    'tag_search_errors_total',
    'Number of Typesense search failures for tags, by search type. '
    "Labels: search_type ('semantic', 'embedding', 'embedding_lookup'). "
    'Failures are silently caught and return an empty list.',
    ['search_type']
)

tag_expansion_total = Counter(
    'tag_expansion_total',
    'Number of LLM tag expansion attempts. '
    "Labels: model ('gemma2', 'qwen25'), success ('true', 'false'). "
    'Expansion enriches the Typesense embedding field to improve semantic search quality; '
    'a failure falls back to the raw tag name.',
    ['model', 'success']
)

tag_expansion_fallback_total = Counter(
    'tag_expansion_fallback_total',
    'Number of times LLM expansion failed and the raw tag name was used as the embedding instead. '
    "Labels: model ('gemma2', 'qwen25'). "
    'Each fallback silently degrades search quality for that tag.',
    ['model']
)

tag_query_duration = Histogram(
    'tag_query_duration_seconds',
    'End-to-end duration of an embedding-based tag search (query_tags). '
    'This path may include a live LLM expansion via qwen25 (3s timeout) if no cached match exists, '
    'followed by a Typesense vector search.'
)

tag_autocomplete_duration = Histogram(
    'tag_autocomplete_duration_seconds',
    'Duration of a semantic tag autocomplete search (autocomplete). '
    'Uses Typesense text search only — no LLM call — so it should be significantly faster than query_tags.'
)

tag_expansion_duration = Histogram(
    'tag_expansion_duration_seconds',
    'Duration of a single LLM tag expansion call. '
    "Labels: model ('gemma2', 'qwen25'). "
    'gemma2 has a 60s timeout and runs in a background worker; '
    'qwen25 has a 3s timeout and runs in the hot request path.',
    ['model']
)
