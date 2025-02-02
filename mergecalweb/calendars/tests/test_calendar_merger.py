# mergecalweb/calendars/tests/test_calendar_merger.py
from http import client as http_client
from typing import TYPE_CHECKING

import pytest

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

from .factories import SourceFactory

if TYPE_CHECKING:
    from django.test import Client

    from mergecalweb.calendars.models import Calendar


@pytest.mark.django_db
def test_calendar_merger_with_test_files(
    calendar: "Calendar",
    mock_calendar_request: None,
    client: "Client",
) -> None:
    """Test merging calendars using test calendar files."""
    # Create sources that point to our test calendar files
    SourceFactory(
        url="http://example.com/basic.ics",
        calendar=calendar,
    )
    SourceFactory(
        url="http://example.com/recurring.ics",
        calendar=calendar,
    )
    SourceFactory(
        url="http://example.com/with_location.ics",
        calendar=calendar,
    )

    # Create merger instance and merge calendars
    merger = CalendarMergerService(calendar)
    merged_calendar = merger.merge()

    # Verify events from all test calendars are present
    assert "Basic Test Event" in merged_calendar
    assert "Recurring Meeting" in merged_calendar
    assert "Event with Location" in merged_calendar

    url = calendar.get_calendar_file_url()

    response = client.get(url)

    # Verify response
    assert response.status_code == http_client.OK
    assert response["Content-Type"] == "text/calendar"

    # Verify calendar content
    content = response.content.decode("utf-8")
    assert "Basic Test Event" in content
    assert "Recurring Meeting" in content
    assert "Event with Location" in content

    # Verify calendar structure
    assert "BEGIN:VCALENDAR" in content
    assert "END:VCALENDAR" in content
    assert f"X-WR-CALNAME:{calendar.name}" in content
