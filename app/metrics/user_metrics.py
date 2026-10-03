from prometheus_client import Counter

user_registered = Counter(
    'user_registered_total',
    'Number of user registration attempts. '
    "Labels: success ('true', 'false'). "
    'A false result means the email is already taken. '
    'Registration also triggers a synchronous confirmation email send.',
    ['success']
)

user_confirmation_email_resent = Counter(
    'user_confirmation_email_resent_total',
    'Number of confirmation email resend requests that resulted in an email being sent. '
    'Requests for already-confirmed or unknown accounts are silently dropped and not counted. '
    'A sustained high rate suggests the confirmation email is not being delivered.'
)

user_deleted = Counter(
    'user_deleted_total',
    'Number of user account deletions. A baseline for churn.'
)
