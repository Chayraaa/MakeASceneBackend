param (
    [string]$Message = "migration"
)

$env:FLASK_ENV = "migration"

flask db migrate -m "$Message"
flask db upgrade