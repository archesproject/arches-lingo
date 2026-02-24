#!/usr/bin/env bash
# post-start.sh — runs each time the codespace starts (including rebuilds/restarts).
# Launches the Webpack dev server and Django development server.

set -euo pipefail

cd /workspaces/arches-lingo
source .venv/bin/activate

echo "==> Starting Webpack dev server in the background..."
nohup npm start > /tmp/webpack-dev-server.log 2>&1 &
echo $! > /tmp/webpack-dev-server.pid

echo "==> Starting Django development server..."
# Run Django in the foreground so the Codespace shows it as the active process.
nohup python manage.py runserver 0.0.0.0:8000 > /tmp/django-dev-server.log 2>&1 &
echo $! > /tmp/django-dev-server.pid

echo "==> Dev servers started."
echo "    Django:  http://localhost:8000"
echo "    Webpack: http://localhost:8022"
echo "    Logs:    /tmp/django-dev-server.log, /tmp/webpack-dev-server.log"
