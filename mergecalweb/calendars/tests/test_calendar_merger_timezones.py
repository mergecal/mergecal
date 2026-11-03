from datetime import UTC
from datetime import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import pytest
from icalendar import Calendar as ICalendar
from icalendar import Event
from icalendar import Timezone

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService

if TYPE_CHECKING:
    from mergecalweb.calendars.models import Calendar

NEW_YORK = ZoneInfo("America/New_York")
PRACTICE_START = datetime(2026, 11, 4, 17, 30, 40, tzinfo=NEW_YORK)


def build_calendar(tzid: str, start: datetime) -> ICalendar:
    ical = ICalendar()
    ical.add("prodid", "-//test//mergecal.org//")
    ical.add("version", "2.0")
    event = Event()
    event.add("uid", f"practice@{tzid}")
    event.add("dtstart", start)
    ical.add_component(event)
    ical.add_missing_timezones()
    return ical


def resolve_like_outlook(vtimezone: Timezone, instant: datetime) -> datetime:
    """Render an instant using only the first STANDARD and first DAYLIGHT.

    Outlook keeps at most one observance of each kind, which is what makes a
    leading placeholder STANDARD harmful.
    """
    trimmed = Timezone(vtimezone)
    seen: set[str | None] = set()
    kept = []
    for observance in vtimezone.subcomponents:
        if observance.name in seen:
            continue
        seen.add(observance.name)
        kept.append(observance)
    trimmed.subcomponents = kept
    return instant.astimezone(trimmed.to_tz(lookup_tzid=False))


@pytest.mark.django_db
def test_placeholder_observance_is_dropped(calendar: "Calendar") -> None:
    ical = build_calendar("America/New_York", PRACTICE_START)
    assert [o.name for o in ical.timezones[0].subcomponents] == [
        "STANDARD",
        "DAYLIGHT",
        "STANDARD",
    ]

    CalendarMergerService(calendar)._drop_placeholder_timezone_observances(ical)  # noqa: SLF001

    assert [o.name for o in ical.timezones[0].subcomponents] == [
        "DAYLIGHT",
        "STANDARD",
    ]


@pytest.mark.django_db
def test_event_keeps_its_wall_time_for_a_one_observance_reader(
    calendar: "Calendar",
) -> None:
    """An event after the autumn transition must not shift by an hour."""
    ical = build_calendar("America/New_York", PRACTICE_START)
    instant = PRACTICE_START.astimezone(UTC)

    before = resolve_like_outlook(ical.timezones[0], instant)
    assert before.strftime("%H:%M") == "18:30"

    CalendarMergerService(calendar)._drop_placeholder_timezone_observances(ical)  # noqa: SLF001

    after = resolve_like_outlook(ical.timezones[0], instant)
    assert after.strftime("%H:%M") == "17:30"
    assert after.utcoffset() == PRACTICE_START.utcoffset()


@pytest.mark.django_db
def test_fixed_offset_timezone_keeps_its_only_observance(
    calendar: "Calendar",
) -> None:
    """A zone without transitions is all placeholder and must survive intact."""
    ical = build_calendar(
        "Asia/Kolkata",
        datetime(2026, 11, 4, 17, 30, tzinfo=ZoneInfo("Asia/Kolkata")),
    )
    assert [o.name for o in ical.timezones[0].subcomponents] == ["STANDARD"]

    CalendarMergerService(calendar)._drop_placeholder_timezone_observances(ical)  # noqa: SLF001

    assert [o.name for o in ical.timezones[0].subcomponents] == ["STANDARD"]
