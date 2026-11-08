from pathlib import Path
from typing import TYPE_CHECKING

import pytest
import responses

from mergecalweb.calendars.services.source_processor import SourceProcessor

from .factories import SourceFactory

if TYPE_CHECKING:
    from mergecalweb.calendars.models import Calendar

LOCAL_CALENDAR = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:local
BEGIN:VEVENT
UID:1
SUMMARY:from local disk
DTSTART:20260101T000000Z
END:VEVENT
END:VCALENDAR
"""


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("filename", "content", "private_text"),
    [
        ("local.ics", LOCAL_CALENDAR, "from local disk"),
        ("secret.txt", "SECRET=hunter2\n", "hunter2"),
    ],
)
def test_feed_body_naming_a_local_file_does_not_read_it(
    http: responses.RequestsMock,
    tmp_path: Path,
    filename: str,
    content: str,
    private_text: str,
) -> None:
    local_file = tmp_path / filename
    local_file.write_text(content)
    source = SourceFactory(url="http://example.com/feed.ics")
    processor = SourceProcessor(source)

    http.get(source.url, body=str(local_file))

    processor.fetch_and_validate()

    assert processor.source_data.ical is None
    assert processor.source_data.error is not None
    assert private_text not in processor.source_data.error


@pytest.mark.django_db
def test_invalid_calendar_header_keeps_the_events(
    calendar: "Calendar",
    http: responses.RequestsMock,
) -> None:
    feed = LOCAL_CALENDAR.replace(
        "PRODID:local\n",
        "PRODID:local\nX-PUBLISHED-TTL:P1H\nREFRESH-INTERVAL:P1H\n",
    )
    source = SourceFactory(url="http://example.com/feed.ics", calendar=calendar)
    processor = SourceProcessor(source)

    http.get(source.url, body=feed)

    processor.fetch_and_validate()

    assert processor.source_data.error is None
    assert processor.source_data.ical is not None
    assert len(processor.source_data.ical.walk("VEVENT")) == 1


@pytest.mark.django_db
def test_body_that_is_not_a_calendar_is_still_an_error(
    calendar: "Calendar",
    http: responses.RequestsMock,
) -> None:
    source = SourceFactory(url="http://example.com/feed.ics", calendar=calendar)
    processor = SourceProcessor(source)

    http.get(source.url, body="false")

    processor.fetch_and_validate()

    assert processor.source_data.ical is None
    assert processor.source_data.error is not None
