from prometheus_client import Counter, Histogram

email_sent = Counter(
    'email_sent_total',
    'Number of outbound email sends. '
    "Labels: type ('confirm', 'password_reset'). "
    'Email sends are synchronous and block the request thread; '
    'a slow email provider directly increases response latency for registration and password reset.',
    ['type']
)

email_send_duration = Histogram(
    'email_send_duration_seconds',
    'Duration of a synchronous outbound email send. '
    "Labels: type ('confirm', 'password_reset'). "
    'This is the primary latency contribution for the registration and password-reset endpoints '
    'since the send happens inline before the response is returned.',
    ['type']
)
