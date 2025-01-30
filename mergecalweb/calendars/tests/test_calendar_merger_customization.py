from http import client as http_client
from typing import TYPE_CHECKING

import pytest

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

from .factories import SourceFactory

if TYPE_CHECKING:
    from django.http import HttpRequest
    from django.test import Client

    from mergecalweb.calendars.models import Calendar


@pytest.mark.django_db
def test_calendar_merger_customizations(
    calendar: "Calendar",
    mock_request: "HttpRequest",
    mock_calendar_request: None,
    client: "Client",
) -> None:
    """Test calendar merging with source customizations enabled."""
    # Set up business tier to enable customizations
    calendar.owner.subscription_tier = calendar.owner.SubscriptionTier.BUSINESS
    calendar.owner.save()

    # Source with custom prefix and all fields included
    SourceFactory(
        url="http://example.com/basic.ics",
        calendar=calendar,
        custom_prefix="[Work]",
        name="Work Calendar",
        include_title=True,
        include_description=True,
        include_location=True,
    )

    # Source with title replaced by source name
    SourceFactory(
        url="http://example.com/recurring.ics",
        calendar=calendar,
        name="Meeting Calendar",
        include_title=False,
        include_description=True,
        include_location=True,
    )

    # Source that excludes meetings and locations
    SourceFactory(
        url="http://example.com/with_location.ics",
        calendar=calendar,
        name="Other Calendar",
        exclude_keywords="meeting",
        include_title=True,
        include_description=True,
        include_location=False,
    )

    # Create merger instance and merge calendars
    merger = CalendarMergerService(calendar, mock_request)
    merged_calendar = merger.merge()

    # Verify customizations are applied
    assert "[Work]: Basic Test Event" in merged_calendar
    assert "Meeting Calendar" in merged_calendar  # Source name instead of title
    assert "Location:" not in merged_calendar  # Location excluded from third source

    url = calendar.get_calendar_file_url()
    response = client.get(url)

    # Verify response
    assert response.status_code == http_client.OK
    assert response["Content-Type"] == "text/calendar"

    # Verify calendar content with customizations
    content = response.content.decode("utf-8")
    assert "[Work]: Basic Test Event" in content
    assert "Meeting Calendar" in content
    assert "Location:" not in content

    # Verify calendar structure
    assert "BEGIN:VCALENDAR" in content
    assert "END:VCALENDAR" in content
    assert f"X-WR-CALNAME:{calendar.name}" in content
