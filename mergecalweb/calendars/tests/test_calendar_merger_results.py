# mergecalweb/calendars/tests/test_calendar_merger.py
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

from .factories import CalendarFactory
from .factories import SourceFactory

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.test import Client

    from mergecalweb.calendars.models import Calendar
    from mergecalweb.users.models import User


@pytest.mark.django_db
def test_calendar_merger_with_test_files(
    business_user: "User",
    mock_request: "HttpRequest",
    mock_calendar_request: None,
    client: "Client",
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
    merger = CalendarMergerService(calendar, mock_request)
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
    merged_calendar = merged_calendar.replace("\r\n", "\n").strip()
    expected_calendar = expected_calendar.replace("\r\n", "\n").strip()

    assert merged_calendar == expected_calendar
