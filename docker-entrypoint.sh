#!/usr/bin/bash

alembic upgrade head

echo "Starting wishlog"
exec gunicorn 'wishlog:create_app()' \
    --bind '0.0.0.0:80'
    --workers 4
