#!/bin/sh
set -e

echo "[entrypoint] Starting gunicorn..."
# If in-memory storage is used, change workers to 1
exec gunicorn -w 4 -b 0.0.0.0:5000 run:app