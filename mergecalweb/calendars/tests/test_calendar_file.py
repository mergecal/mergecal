from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.core.cache import cache
from django.urls import reverse
from icalendar import Calendar as ICalendar

from mergecalweb.calendars.cache import source_data_cache_key

from .factories import CalendarFactory
from .factories import SourceFactory

if TYPE_CHECKING:
    from pathlib import Path

    import responses
    from django.test import Client

    from mergecalweb.users.models import User


@pytest.mark.django_db
def test_calendar_file_serves_and_caches_merged_output(
    business_user: User,
    client: Client,
    http: responses.RequestsMock,
    test_calendars_dir: Path,
) -> None:
    calendar = CalendarFactory(
        owner=business_user,
        update_frequency_seconds=7200,
        remove_branding=True,
    )
    source_urls = []
    for filename in ("basic.ics", "recurring.ics", "with_location.ics"):
        source_url = f"https://feeds.example.test/{filename}"
        source_urls.append(source_url)
        SourceFactory(url=source_url, calendar=calendar)
        http.get(source_url, body=(test_calendars_dir / filename).read_bytes())

    url = reverse("calendars:calendar_file_ics", args=[calendar.uuid])
    response = client.get(url)

    assert response.status_code == HTTPStatus.OK
    assert response["Content-Type"] == "text/calendar"
    assert (
        response["Content-Disposition"] == f'attachment; filename="{calendar.uuid}.ics"'
    )
    assert response["Cache-Control"] == "public, max-age=7200"

    merged = ICalendar.from_ical(response.content)
    summaries = sorted(str(event["SUMMARY"]) for event in merged.walk("VEVENT"))
    assert summaries == ["Basic Test Event", "Event with Location", "Recurring Meeting"]
    assert merged["X-WR-CALNAME"] == calendar.name
    assert merged["X-PUBLISHED-TTL"] == "PT2H"
    assert merged.decoded("REFRESH-INTERVAL") == timedelta(hours=2)

    # Clear the source cache so only the merged-output cache can prevent refetching.
    cache.delete_many([source_data_cache_key(source_url) for source_url in source_urls])
    cached_response = client.get(url)

    assert cached_response.status_code == HTTPStatus.OK
    assert cached_response.content == response.content
    assert len(http.calls) == len(source_urls)


@pytest.mark.django_db
def test_adding_source_reuses_validation_fetch_for_merged_feed(
    business_user: User,
    client: Client,
    http: responses.RequestsMock,
    test_calendars_dir: Path,
) -> None:
    calendar = CalendarFactory(owner=business_user)
    source_url = "https://feeds.example.test/basic.ics"
    http.get(source_url, body=(test_calendars_dir / "basic.ics").read_bytes())
    client.force_login(business_user)

    response = client.post(
        reverse("calendars:source_add", args=[calendar.uuid]),
        {"name": "Basic", "url": source_url},
    )
    assert response.status_code == HTTPStatus.FOUND
    client.get(reverse("calendars:calendar_file_ics", args=[calendar.uuid]))

    assert len(http.calls) == 1


@pytest.mark.django_db
def test_editing_calendar_rebuilds_merged_feed_without_refetching_sources(
    business_user: User,
    client: Client,
    http: responses.RequestsMock,
    test_calendars_dir: Path,
) -> None:
    calendar = CalendarFactory(owner=business_user, name="Before")
    source_url = "https://feeds.example.test/basic.ics"
    SourceFactory(url=source_url, calendar=calendar)
    http.get(source_url, body=(test_calendars_dir / "basic.ics").read_bytes())
    url = reverse("calendars:calendar_file_ics", args=[calendar.uuid])
    client.get(url)

    calendar.name = "After"
    calendar.save()
    response = client.get(url)

    assert ICalendar.from_ical(response.content)["X-WR-CALNAME"] == "After"
    assert len(http.calls) == 1
