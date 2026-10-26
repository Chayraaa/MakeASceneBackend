param (
    [string]$Message = "migration",
    [switch]$UpgradeOnly
)

$env:FLASK_ENV = "migration"

if ($UpgradeOnly) {
    flask db upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Database upgrade failed."
    }
    return
}

# Apply existing revisions before generating a revision for further model changes.
flask db upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Applying existing migrations failed. Migration generation was skipped."
}

flask db migrate -m "$Message"
if ($LASTEXITCODE -ne 0) {
    throw "Migration generation failed. Database upgrade was skipped."
}

flask db upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Database upgrade failed."
}
