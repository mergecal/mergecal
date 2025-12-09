"""Tests for Windows timezone handling."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

from .factories import SourceFactory

if TYPE_CHECKING:
    from mergecalweb.calendars.models import Calendar


@pytest.mark.django_db
def test_windows_timezone_handling(
    calendar: Calendar,
    mock_calendar_request: None,
) -> None:
    """Test Windows timezone identifiers are converted to IANA identifiers."""
    # Create a source with a calendar that has Windows timezone identifier
    SourceFactory(
        url="http://example.com/windows_timezone.ics",
        calendar=calendar,
    )

    # Merge the calendar - this should not raise UnknownTimeZoneError
    merger = CalendarMergerService(calendar)
    merged_calendar = merger.merge()

    # Verify the event is present in the merged calendar
    assert "Test Event with Windows Timezone" in merged_calendar
    assert "BEGIN:VCALENDAR" in merged_calendar
    assert "END:VCALENDAR" in merged_calendar


@pytest.mark.django_db
def test_multiple_calendars_with_mixed_timezones(
    calendar: Calendar,
    mock_calendar_request: None,
) -> None:
    """Test merging calendars with both Windows and IANA timezone identifiers."""
    # Create sources with different timezone identifiers
    SourceFactory(
        url="http://example.com/windows_timezone.ics",
        calendar=calendar,
    )
    SourceFactory(
        url="http://example.com/basic.ics",  # Calendar without special timezone
        calendar=calendar,
    )

    # Merge calendars - should handle both gracefully
    merger = CalendarMergerService(calendar)
    merged_calendar = merger.merge()

    # Verify events from both calendars are present
    assert "Test Event with Windows Timezone" in merged_calendar
    assert "Basic Test Event" in merged_calendar
