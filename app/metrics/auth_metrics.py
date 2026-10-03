from prometheus_client import Counter

auth_login_attempts = Counter(
    'auth_login_attempts_total',
    'Number of login attempts split by authentication method and outcome. '
    "Labels: method ('local', 'google'), success ('true', 'false'). "
    'A high local failure rate is a brute-force signal; '
    'google failures indicate OAuth provider issues.',
    ['method', 'success']
)

auth_token_refresh = Counter(
    'auth_token_refresh_total',
    'Number of refresh token exchange attempts, labelled by outcome. '
    "Labels: result ('success', 'not_found', 'revoked', 'expired'). "
    "A spike in 'revoked' results is a token-theft indicator - "
    'it means a token that was already rotated is being reused.',
    ['result']
)

auth_email_confirmation = Counter(
    'auth_email_confirmation_total',
    'Number of email confirmation link clicks, labelled by outcome. '
    "Labels: result ('success', 'not_found', 'revoked', 'expired'). "
    "High 'expired' counts suggest the confirmation window is too short for your user base.",
    ['result']
)

auth_password_reset_requested = Counter(
    'auth_password_reset_requested_total',
    'Number of password reset email requests. '
    'A high rate relative to registered users is an indicator of email enumeration attacks, '
    'since the endpoint reveals whether an account exists via its response code.'
)

auth_password_reset_completed = Counter(
    'auth_password_reset_completed_total',
    'Number of password reset completions. '
    "Labels: success ('true', 'false'). "
    'Combine with requested total to compute funnel completion rate.',
    ['success']
)

auth_logout = Counter(
    'auth_logout_total',
    'Number of explicit logout operations. '
    'Each logout revokes all active refresh tokens for the user. '
    'A baseline for active session churn.'
)
