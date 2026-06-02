"""Tests for the prefetch_calendars management command."""

from io import StringIO
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest
from django.core.cache import cache
from django.core.management import call_command

from mergecalweb.calendars.cache import calendar_output_cache_key
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

from .factories import CalendarFactory
from .factories import SourceFactory

if TYPE_CHECKING:
    from mergecalweb.calendars.models import Calendar


def _run(**kwargs: object) -> str:
    out = StringIO()
    call_command("prefetch_calendars", stdout=out, **kwargs)
    return out.getvalue()


@pytest.mark.django_db
def test_prefetch_populates_output_cache(
    calendar: "Calendar",
    mock_calendar_request: None,
    settings,
) -> None:
    SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    settings.CALENDAR_PREFETCH_USER_IDS = [calendar.owner.id]
    cache.delete(calendar_output_cache_key(calendar.uuid))

    _run()

    cached = cache.get(calendar_output_cache_key(calendar.uuid))
    assert cached is not None
    assert "Basic Test Event" in cached


@pytest.mark.django_db
def test_prefetch_skips_non_opted_in_users(
    calendar: "Calendar",
    mock_calendar_request: None,
    settings,
) -> None:
    SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    settings.CALENDAR_PREFETCH_USER_IDS = [calendar.owner.id + 9999]
    cache.delete(calendar_output_cache_key(calendar.uuid))

    _run()

    assert cache.get(calendar_output_cache_key(calendar.uuid)) is None


@pytest.mark.django_db
def test_prefetch_excludes_free_tier(
    mock_calendar_request: None,
    settings,
) -> None:
    free_user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
    free_cal = CalendarFactory(owner=free_user)
    SourceFactory(url="http://example.com/basic.ics", calendar=free_cal)
    settings.CALENDAR_PREFETCH_USER_IDS = [free_user.id]
    cache.delete(calendar_output_cache_key(free_cal.uuid))

    _run()

    assert cache.get(calendar_output_cache_key(free_cal.uuid)) is None


@pytest.mark.django_db
def test_prefetch_dry_run_does_not_warm(
    calendar: "Calendar",
    mock_calendar_request: None,
    settings,
) -> None:
    SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    settings.CALENDAR_PREFETCH_USER_IDS = [calendar.owner.id]
    cache.delete(calendar_output_cache_key(calendar.uuid))

    output = _run(dry_run=True)

    assert cache.get(calendar_output_cache_key(calendar.uuid)) is None
    assert str(calendar.uuid) in output


@pytest.mark.django_db
def test_prefetch_empty_user_ids_warms_nothing(
    calendar: "Calendar",
    mock_calendar_request: None,
    settings,
) -> None:
    SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    settings.CALENDAR_PREFETCH_USER_IDS = []
    cache.delete(calendar_output_cache_key(calendar.uuid))

    output = _run()

    assert cache.get(calendar_output_cache_key(calendar.uuid)) is None
    assert "0 calendar(s)" in output


@pytest.mark.django_db
def test_prefetch_failure_increments_failed_counter(
    calendar: "Calendar",
    settings,
) -> None:
    settings.CALENDAR_PREFETCH_USER_IDS = [calendar.owner.id]
    cache.delete(calendar_output_cache_key(calendar.uuid))

    with patch(
        "mergecalweb.calendars.management.commands.prefetch_calendars.CalendarMergerService.merge",
        side_effect=RuntimeError("boom"),
    ):
        output = _run()

    assert "1 failed" in output
    assert cache.get(calendar_output_cache_key(calendar.uuid)) is None
