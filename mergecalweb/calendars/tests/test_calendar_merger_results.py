from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from django.contrib.sites.models import Site
from icalendar import Calendar as ICalendar

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

from .factories import CalendarFactory
from .factories import SourceFactory

if TYPE_CHECKING:
    import responses
    from django.test import Client

    from mergecalweb.users.models import User


@pytest.mark.django_db
def test_calendar_merger_with_test_files(
    business_user: User,
    mock_calendar_request: None,
    client: Client,
) -> None:
    """Test merging calendars using test calendar files."""
    # Create deterministic calendar
    calendar: Calendar = CalendarFactory(
        name="Test Calendar",
        uuid="12345678-1234-5678-1234-567812345678",
        owner=business_user,
    )

    # Create sources
    test_sources = [
        "airbnb.ics",
        "bookinghound.ics",
        "google.ics",
        "officeholidays.ics",
        "teamsnap.ics",
        "vrbo.ics",
    ]
    for source in test_sources:
        SourceFactory(url=f"http://example.com/{source}", calendar=calendar)

    # Merge calendars
    merger = CalendarMergerService(calendar)
    merged_calendar = merger.merge()

    # Load and compare with golden file
    golden_file = Path(__file__).parent / "calendars/golden_merged_calendar.ics"

    # Uncomment to update golden file
    write_to_file = False
    if write_to_file:
        with golden_file.open("w", encoding="utf-8", newline="\n") as f:
            f.write(merged_calendar)

    with golden_file.open("r", encoding="utf-8") as f:
        expected_calendar = f.read()

    # Simple normalize both calendars
    merged_calendar = "\n".join(s.rstrip() for s in merged_calendar.splitlines())
    expected_calendar = "\n".join(s.rstrip() for s in expected_calendar.splitlines())

    assert merged_calendar == expected_calendar


@pytest.mark.django_db
def test_teamsnap_feed_keeps_its_own_timezone(
    business_user: User,
    mock_calendar_request: None,
) -> None:
    calendar: Calendar = CalendarFactory(owner=business_user)
    SourceFactory(
        url="http://example.com/teamsnap_x_wr_timezone.ics",
        calendar=calendar,
    )

    merged = CalendarMergerService(calendar).merge()

    timezones = ICalendar.from_ical(merged.encode()).timezones
    assert [timezone.tz_name for timezone in timezones] == ["America/New_York"]
    observances = [
        (observance.name, "RRULE" in observance, "RDATE" in observance)
        for observance in timezones[0].subcomponents
    ]
    assert observances == [("DAYLIGHT", True, False), ("STANDARD", True, False)]


@pytest.mark.django_db
def test_merge_keeps_events_from_direct_and_nested_sources(
    calendar: Calendar,
    http: responses.RequestsMock,
    test_calendars_dir: Path,
) -> None:
    nested_calendar = Calendar.objects.create(
        name="Nested calendar",
        owner=calendar.owner,
    )
    site_domain = Site.objects.get_current().domain
    nested_feed_url = f"https://{site_domain}{nested_calendar.get_calendar_file_url()}"
    SourceFactory(calendar=calendar, url=nested_feed_url)

    nested_source_url = "https://feeds.example.test/basic.ics"
    SourceFactory(calendar=nested_calendar, url=nested_source_url)
    http.get(nested_source_url, body=(test_calendars_dir / "basic.ics").read_bytes())

    direct_source_url = "https://feeds.example.test/with_location.ics"
    SourceFactory(calendar=calendar, url=direct_source_url)
    http.get(
        direct_source_url,
        body=(test_calendars_dir / "with_location.ics").read_bytes(),
    )

    merged = ICalendar.from_ical(CalendarMergerService(calendar).merge())

    event_uids = sorted(str(event["UID"]) for event in merged.walk("VEVENT"))
    assert event_uids == ["test-event-001@mergecal.org", "test-event-003@mergecal.org"]
