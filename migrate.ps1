param (
    [string]$Message = "migration",
    [switch]$UpgradeOnly
)

$migrationPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $migrationPython)) {
    throw "Project virtual environment not found at $migrationPython. Create .venv and install requirements.txt first."
}

$env:FLASK_ENV = "migration"

if ($UpgradeOnly) {
    & $migrationPython -m flask db upgrade
    if ($LASTEXITCODE -ne 0) {
        throw "Database upgrade failed."
    }
    return
}

# Apply existing revisions before generating a revision for further model changes.
& $migrationPython -m flask db upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Applying existing migrations failed. Migration generation was skipped."
}

& $migrationPython -m flask db migrate -m "$Message"
if ($LASTEXITCODE -ne 0) {
    throw "Migration generation failed. Database upgrade was skipped."
}

& $migrationPython -m flask db upgrade
if ($LASTEXITCODE -ne 0) {
    throw "Database upgrade failed."
}
