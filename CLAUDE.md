# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

MergeCal is a Django webapp that allows users to merge multiple iCalendar feeds into a single feed. The application is built with Django 4.0+, uses PostgreSQL for the database, Redis for caching and message broker, and Celery for background task processing.

## Architecture

### Core Components

- **mergecalweb/calendars/** - Main calendar merging functionality
  - `models.py`: Calendar and Source models with subscription tier validation
  - `tasks.py`: Celery tasks for periodic calendar updates
  - `utils.py`: Calendar combining logic (`combine_calendar` function)
  - `services/`: Service layer for calendar operations
    - `calendar_merger_service.py`: Handles calendar merging logic
    - `source_processor.py`: Processes individual calendar sources
    - `source_service.py`: Source CRUD operations
  - `meetup.py`: Special handling for Meetup.com calendar URLs
  - `calendar_fetcher.py`: Fetches iCal data from external URLs

- **mergecalweb/users/** - Custom user model with subscription tiers
  - Subscription tiers: PERSONAL, BUSINESS, SUPPORTER
  - Tier-based permissions control calendar/source limits and features

- **mergecalweb/billing/** - Stripe integration for subscriptions (uses dj-stripe)

- **mergecalweb/blog/** - Blog functionality

- **mergecalweb/core/** - Shared utilities and constants
  - `constants.py`: Contains CalendarLimits and SourceLimits for subscription tiers

- **config/** - Django settings and configuration
  - `settings/base.py`, `settings/local.py`, `settings/production.py`
  - `celery_app.py`: Celery configuration
  - `urls.py`: URL routing

### How Calendar Merging Works

1. Users create a Calendar and add multiple Sources (iCal feed URLs) to it
2. Events are merged into a single iCal feed with deduplication by UID
3. The merged calendar is cached (BUSINESS and up users change control cache duration)
4. Users subscribe to their merged calendar via a unique UUID-based URL

### Subscription Tier System

The User model (`mergecalweb/users/models.py`) implements a tier system that controls:
- Number of calendars a user can create (CalendarLimits)
- Number of sources per calendar (SourceLimits)
- Update frequency customization (Business/Supporter only)
- Branding removal (Business/Supporter only)
- Source customization features (Business/Supporter only)

Validation is enforced in model `clean()` methods for Calendar and Source.

## Development Commands

### Setup

```bash
# Install dependencies
pip install -r requirements/local.txt

# Run migrations
python manage.py migrate

# Create superuser
python manage.py createsuperuser

# Run development server
python manage.py runserver
```

### Celery

Celery is required for background calendar fetching and merging.

```bash
# Run Celery worker
celery -A config.celery_app worker -l info

# Run Celery beat scheduler (for periodic tasks)
celery -A config.celery_app beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Testing

```bash
# Run all tests
pytest

# Run tests for a specific app
pytest mergecalweb/calendars/tests/

# Run a specific test file
pytest mergecalweb/calendars/tests/test_models.py

# Run with coverage
pytest --cov=mergecalweb

# Run tests and keep the database
pytest --reuse-db
```

### Linting and Formatting

```bash
# Run Ruff linter
ruff check .

# Run Ruff linter with auto-fix
ruff check --fix .

# Run Ruff formatter
ruff format .

# Run djLint on templates
djlint --reformat mergecalweb/templates/

# Run pre-commit hooks manually
pre-commit run --all-files
```

### Database

```bash
# Create migrations
python manage.py makemigrations

# Apply migrations
python manage.py migrate

# Create a database backup (if using PostgreSQL locally)
pg_dump mergecalweb > backup.sql
```

## Key Configuration

- **Settings**: Django settings use `django-environ` to read from `.env` file
- **Database**: PostgreSQL (default: `postgres:///mergecalweb`)
- **Cache/Broker**: Redis (default: `redis://localhost:6379/0`)
- **Static Files**: Managed by WhiteNoise
- **Authentication**: django-allauth with Google OAuth2 support, MFA enabled
- **Payments**: Stripe via dj-stripe

## Important Implementation Notes

### Calendar Validation

- Calendar sources are validated on save via `validate_ical_url` in `calendars/models.py`
- Meetup.com URLs have special handling and skip standard iCal validation
- Local MergeCal URLs (recursive calendars) are allowed but validated for existence

### Caching Strategy

- PERSONAL tier users get 24-hour cached calendar data to reduce load
- BUSINESS tier users can control the cache duration.
- Cache key format: `calendar_str_{calendar.uuid}`

### Special URL Handling

- Each Calendar has a unique UUID for public access
- Calendar URLs: `/calendars/{uuid}/file/` (iCal format)
- Deprecated domains (calmerge.habet.dev, mergecalweb.habet.dev) show warnings

### Source Processing

- Events are deduplicated by UID during merging
- Source name can be prefixed to event titles if `include_source=True`
- MergeCal branding is added to event descriptions unless user has opted out
- Custom prefixes and keyword exclusion available for Business/Supporter tiers

## Django Apps Structure

The main application code lives in `mergecalweb/` with these Django apps:
- `calendars` - Calendar and source management (primary app)
- `users` - User authentication and subscription management
- `billing` - Stripe integration
- `blog` - Blog posts
- `core` - Shared utilities

Built with [Cookiecutter Django](https://github.com/cookiecutter/cookiecutter-django/).

## Environment Variables

Key environment variables (defined in `.env`):
- `DJANGO_DEBUG` - Debug mode
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `DJANGO_SECRET_KEY` - Django secret key
- `STRIPE_PRICE_TABLE_ID` - Stripe pricing table
