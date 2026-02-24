#!/usr/bin/env bash
# on-create.sh — runs once when the codespace container is first created.
# Installs Python/Node dependencies, sets up the database, and loads the package.

set -euo pipefail

cd /workspaces/arches-lingo

echo "==> Creating Python virtual environment..."
python -m venv .venv
source .venv/bin/activate

echo "==> Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -e .
pip install livereload coverage pre-commit

echo "==> Installing Node dependencies..."
npm install

echo "==> Generating frontend configuration..."
# frontend_configuration/ is auto-generated on Django startup via ArchesAppConfig.ready()
python manage.py check --deploy 2>/dev/null || true

echo "==> Setting up the database..."
python manage.py setup_db --force

echo "==> Loading the arches-lingo package..."
python manage.py packages -o load_package -a arches_lingo -dev -y

echo "==> Running initial webpack build..."
npm run build_development_unsafe

echo "==> on-create complete."
