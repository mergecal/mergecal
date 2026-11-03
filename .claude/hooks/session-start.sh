#!/bin/bash
# Makes a cloud session ready to run pytest, ruff and mypy. The container starts with
# Postgres installed but stopped, no database and no project dependencies. Safe to re-run.
set -euo pipefail

[ "${CLAUDE_CODE_REMOTE:-}" = "true" ] || exit 0
cd "${CLAUDE_PROJECT_DIR:-$(git rev-parse --show-toplevel)}"

pg_isready -q || service postgresql start
until pg_isready -q; do sleep 1; done

# The default DATABASE_URL is postgres:///mergecalweb, which connects as the current OS user.
user="$(whoami)"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_roles WHERE rolname='$user'" | grep -q 1 \
  || sudo -u postgres psql -qc "CREATE ROLE \"$user\" SUPERUSER LOGIN"
sudo -u postgres psql -tAc "SELECT 1 FROM pg_database WHERE datname='mergecalweb'" | grep -q 1 \
  || sudo -u postgres createdb mergecalweb -O "$user"

python -m pip install --quiet -r requirements/local.txt

# Import the whole project, so a session never starts believing it can run the tests when
# something the suite imports is broken.
python manage.py check --settings=config.settings.test >/dev/null

echo "Ready: Postgres up, mergecalweb database present, $(python -V) and dependencies installed."
