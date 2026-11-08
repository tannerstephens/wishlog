#!/usr/bin/bash
set -euo pipefail

# Runs before gunicorn starts, so it also creates the secret key file once,
# before the workers start and read it.
alembic upgrade head

echo "Starting wishlog"
exec gunicorn 'wishlog:create_app()' \
    --bind '0.0.0.0:80' \
    --workers 4
