#!/bin/bash

export FLASK_ENV=migration

MESSAGE="${1:-migration}"

flask db migrate -m "$MESSAGE"
flask db upgrade