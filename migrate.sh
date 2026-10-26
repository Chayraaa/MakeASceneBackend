#!/bin/bash
source secrets.env
export FLASK_ENV=migration

MESSAGE="migration"
UPGRADE_ONLY=false

for arg in "$@"; do
    case "$arg" in
        --upgrade-only) UPGRADE_ONLY=true ;;
        *) MESSAGE="$arg" ;;
    esac
done

if [ "$UPGRADE_ONLY" = false ]; then
    flask db migrate -m "$MESSAGE" || exit $?
fi
flask db upgrade
