# Agent Handbook
- Claude Code web sessions are provisioned by `.claude/hooks/session-start.sh`. Redis/Celery aren't needed for tests. Run tools as `python -m pytest` and `python -m mypy` there, because the binaries on PATH may not see the project's dependencies.
- MergeCal merges iCal feeds; Django 5.0, Postgres, Redis, Celery. Frontend is Django templates with Bootstrap 5 and crispy forms.
- Never fetch calendar URLs (mergecal.org/calendars/*, source ICS feeds, any user-shared ICS link), even ones that look public: they contain private user data. If you need to inspect ICS content, ask for a sanitized excerpt.
- Core app `mergecalweb/calendars/`: `models.py` enforces tier limits; `services/` orchestrate merging.
- Calendars dedupe events by UID; cache duration varies per subscription tier.
- `calendar_merger_service.py` merges sources; `source_processor.py` validates feeds; `fetching/fetcher.py` pulls remote ICS.
- Cache pre-warming runs via `python manage.py prefetch_calendars` (cron), not Celery.
- Meetup URLs handled in `meetup.py`; recursive MergeCal feeds are supported with existence checks.
- `mergecalweb/users/` defines PERSONAL/BUSINESS/SUPPORTER tiers controlling calendar counts and feature access.
- Branding opt-out and custom update cadence live behind Business/Supporter tiers.
- Billing app integrates Stripe via dj-stripe; blog/core provide marketing content and shared utilities.
- Settings live in `config/settings/`; Celery setup in `config/celery_app.py`; URLs in `config/urls.py`.
- Periodic tasks are django-celery-beat rows in the DB (DatabaseScheduler), not defined in code.
- Install deps: `pip install -r requirements/local.txt`.
- Prep DB: `python manage.py migrate`; create admin via `python manage.py createsuperuser` when needed.
- Run dev server: `python manage.py runserver`.
- Celery worker: `celery -A config.celery_app worker -l info`.
- Optional beat: `celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler`.
- Full tests: `pytest` (auto uses `config.settings.test`, reuses DB); reuse DB flag optional.
- Scoped tests: `pytest mergecalweb/calendars/tests/`; single test `pytest path/to/test_file.py::TestCase::test_name`.
- Coverage: `pytest --cov=mergecalweb`.
- Lint: `ruff check .`; auto-fix `ruff check --fix`; format via `ruff format .`.
- Templates: `djlint --reformat mergecalweb/templates/` then `djlint`.
- Typing: `mypy --config-file pyproject.toml mergecalweb config` (targets required); favor explicit annotations and `from __future__ import annotations`.
- Lint/typing baseline is not clean on `main`: mypy reports dozens of errors, and `ruff check .` flags unused `noqa` comments (RUF100) because the pinned ruff is older than pre-commit's. Compare against `main` before fixing "your" errors.
- Style: 4-space Python, 2-space templates, double quotes, avoid bare excepts.
- Logging: Structured logging for filtering user journeys, billing flows, calendar operations:
  - ALWAYS: `extra={"event": LogEvent.CONSTANT, ...}` (import from `mergecalweb.core.logging_events`)
  - User context: `"user_id": user.pk, "email": user.email` - filter all actions by user
  - Calendar: `"calendar_uuid": calendar.uuid, "calendar_name": calendar.name`
  - Source: `"source_id": source.pk, "source_url": source.url`
  - Many events use params for specificity: `"action": "created"`, `"status": "success"`, `"error_type": "timeout"`
  - Levels: `logger.info` (normal ops), `logger.warning` (expected failures), `logger.exception` (Sentry alerts)
  - Debug logs may skip event constant if internal/verbose
  - Pre-commit hook (semgrep) enforces logging conventions automatically

## General Coding Preferences
- Always prefer simple solutions.
- Avoid duplication: check whether the codebase already has similar code and functionality before writing more.
- Only make changes that are requested, or that you are confident are well understood and related to the request.
- When fixing a bug, exhaust the existing implementation before introducing a new pattern or technology. If you do introduce one, remove the old implementation so there is no duplicate logic.
- Think about what other areas of code a change might affect.
- Keep the codebase clean and organized. Avoid writing scripts to files, especially ones likely to run only once.
- Never add mock data to functions. Mocks belong only in tests or utilities used only by tests.
- Never overwrite the `.env` file without asking first.
- Avoid code comments. Only add one when there is something important a reader can't learn from the code itself.
- Write code that reads top to bottom. Prefer plain `if X: raise Y` / `return Z` over lookup dicts, context managers, or other indirection.
- Keep code inline. Only extract a helper function once the same code has two callers.
- Handle errors explicitly and avoid silent failures. Always validate user input server-side.
- Use the Django ORM where possible, with lazy querysets and `select_related` / `prefetch_related` where needed.
- Use signals sparingly and document them well.

## Python Conventions
- New plain data classes use `attrs` (`@attrs.frozen` / `@attrs.define`), not `dataclasses`. Leave existing dataclasses alone. `attrs` isn't a direct dependency yet, so add it to `requirements/base.txt` with its first use.
- New models extend `mergecalweb.core.models.TimeStampedModel`.

### Interfaces and services
- An interface is anything a caller comes in through: an HTTP view, a webhook, a management command, a Celery task.
- Interfaces stay thin. They call a service (or similar) to do the work and get data back.
- Services return data (attrs classes, model instances) or raise exceptions. They never produce text meant for a particular audience.
- Each interface translates the result for whoever uses it. A command prints facts for a developer, and a view renders for its user.
- When several interfaces need the same translation, move it into its own shared module rather than into the service.

### Exceptions
- Wrap third-party errors in our own exception types, named so the caller knows how to act: `UnsupportedSourceError`, not a re-raised `requests` exception.
- An exception's name should be enough for the caller to act on, so don't pass message strings.
- If the caller needs data from the error, make the exception an attrs class with typed fields.

### Testing
- Unit tests call functions directly and avoid mocking, especially for a function that does one thing.
- When a function calls an external API, fake it at the HTTP layer so the real client runs: `responses` for `requests`, `respx` for `httpx`. Neither is installed yet, so add the one you need to `requirements/local.txt` with its first use.
- Integration tests exercise an interface (the test client for views and webhooks, `call_command` for commands). Mocking the service behind it is fine; the test checks wiring, status codes and output.

## Planning Work
- Keep it lean. Build only what the next milestone needs, and leave everything else out until real usage shows it's needed.
- Work in small PRs, one step at a time. Each PR is reviewed and merged before the next one starts.
- Allow for real-world cases in the design, even when the first version is basic. For example, the same user doing the same thing again later.

## Git Workflow
- All work is done on a new branch and merged through a pull request. Never commit directly to `main`.
- Every commit must be atomic: one logical change that stands on its own.
- History on a feature branch may be rewritten (rebase, squash, reorder, amend) to keep commits atomic before merging.
- Commit messages and PR descriptions explain *why* the change was made, not *what* changed; the diff already shows what.
