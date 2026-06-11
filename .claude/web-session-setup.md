# Claude Code Web Session Setup

Remote Claude Code sessions run in a fresh container: the repo is cloned,
but project dependencies are not installed and PostgreSQL is not running.
Do this before running tests or management commands.

## 1. Install dependencies

```bash
pip install -r requirements/local.txt
```

## 2. Start PostgreSQL and create the database

Postgres is installed in the container but down. The default
`DATABASE_URL` is `postgres:///mergecalweb` (unix socket, current OS user),
so the current user needs a login role and the database must exist:

```bash
service postgresql start
sudo -u postgres psql -c "CREATE ROLE $(whoami) SUPERUSER LOGIN;"
sudo -u postgres createdb mergecalweb -O "$(whoami)"
```

Redis/Celery are NOT required for the test suite.

## 3. Run tools through the project Python

The `pytest` and `mypy` binaries on PATH may be isolated tool installs
that cannot see the project's dependencies. Always invoke them as modules:

```bash
python -m pytest
python -m mypy --config-file pyproject.toml mergecalweb config
```

## Known baseline failures (do not chase these)

Verify your change against `main` before attributing failures to it:

- `ruff check .` fails on `docs/conf.py` (PGH004) on a clean checkout.
- mypy reports dozens of pre-existing errors on `main`. Compare error
  counts against `main` rather than aiming for a clean run.
