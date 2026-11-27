from datetime import UTC
from datetime import datetime

import pytest

from mergecalweb.calendars.meetup import clean_meetup_description
from mergecalweb.calendars.meetup import extract_meetup_group_name
from mergecalweb.calendars.meetup import fetch_and_create_meetup_calendar
from mergecalweb.calendars.meetup import is_meetup_url


@pytest.mark.parametrize(
    "url",
    [
        "https://www.meetup.com/some-group/events/ical/",
        "https://meetup.com/some-group/events/ical/",
        "https://WWW.MEETUP.COM:443/some-group/",
    ],
)
def test_meetup_urls_are_recognised(url):
    assert is_meetup_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://notmeetup.com/cal.ics",
        "https://example.com/cal.ics?from=meetup.com",
        "https://example.com/meetup.com/cal.ics",
        "https://meetup.com.example.com/cal.ics",
    ],
)
def test_other_urls_are_not_meetup(url):
    assert not is_meetup_url(url)


GROUP_URL = "https://www.meetup.com/example-board-gamers/events/"
API_URL = "https://api.meetup.com/example-board-gamers/events"


@pytest.fixture
def meetup_events_json(test_calendars_dir):
    return (test_calendars_dir / "meetup_events.json").read_bytes()


def test_group_name_is_first_path_segment():
    assert extract_meetup_group_name(GROUP_URL) == "example-board-gamers"


def test_description_is_converted_to_plain_text():
    description = (
        "line one<br>line two  **bold**"
        "&lt;p&gt;See [docs](https://example.com)&lt;/p&gt;"
    )

    assert clean_meetup_description(description) == (
        "line one\nline two bold\n\nSee docs (https://example.com)"
    )


def test_api_events_become_calendar_events(http, meetup_events_json):
    http.get(API_URL, body=meetup_events_json, content_type="application/json")

    cal = fetch_and_create_meetup_calendar(GROUP_URL)

    upcoming, cancelled = cal.walk("VEVENT")
    assert upcoming["summary"] == "Monthly Board Game Night"
    assert upcoming["uid"] == "meetup-300000001@mergecal.org"
    assert upcoming.decoded("dtstart") == datetime(2026, 1, 1, 19, tzinfo=UTC)
    assert upcoming.decoded("dtend") == datetime(2026, 1, 1, 22, tzinfo=UTC)
    assert upcoming["status"] == "CONFIRMED"
    assert upcoming["location"] == ("Example Cafe, 1 Main St, Springfield, XX, us")
    assert (upcoming["geo"].latitude, upcoming["geo"].longitude) == (40.5, -74.25)
    assert upcoming["description"].endswith(
        "How to find us: Back room, look for the dice sign",
    )
    assert upcoming["x-meetup-yes-rsvp-count"] == "7"
    assert cancelled["status"] == "CANCELLED"
    assert "location" not in cancelled


def test_api_http_error_returns_none(http):
    http.get(API_URL, status=404)

    assert fetch_and_create_meetup_calendar(GROUP_URL) is None


def test_unexpected_api_response_returns_none(http):
    http.get(API_URL, json={"errors": [{"code": "group_error"}]})

    assert fetch_and_create_meetup_calendar(GROUP_URL) is None
