from icalendar import Calendar
from icalendar import Timezone

from mergecalweb.calendars.tz_normalize import normalize_tzids


def test_normalize_tzids_rewrites_windows_tzid_on_datetime_properties() -> None:
    calendar = Calendar.from_ical(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-event-1
DTSTART;TZID=Eastern Standard Time:20260101T090000
DTEND;TZID=Eastern Standard Time:20260101T100000
END:VEVENT
END:VCALENDAR
""",
    )

    normalized_calendar = normalize_tzids(calendar)
    event = normalized_calendar.walk("VEVENT")[0]

    assert event.get("DTSTART").params["TZID"] == "America/New_York"
    assert event.get("DTEND").params["TZID"] == "America/New_York"


def test_normalize_tzids_renames_vtimezone_tzid() -> None:
    calendar = Calendar()
    vtimezone = Timezone()
    vtimezone.add("TZID", "Eastern Standard Time")
    calendar.add_component(vtimezone)

    normalized_calendar = normalize_tzids(calendar)
    vtimezones = [
        component
        for component in normalized_calendar.subcomponents
        if component.name == "VTIMEZONE"
    ]

    assert str(vtimezones[0].get("TZID")) == "America/New_York"


def test_normalize_tzids_leaves_iana_tzid_unchanged() -> None:
    calendar = Calendar.from_ical(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-event-2
DTSTART;TZID=America/Chicago:20260102T090000
END:VEVENT
END:VCALENDAR
""",
    )

    normalized_calendar = normalize_tzids(calendar)
    event = normalized_calendar.walk("VEVENT")[0]

    assert event.get("DTSTART").params["TZID"] == "America/Chicago"


def test_normalize_tzids_rewrites_exdate_and_rdate_with_list_values() -> None:
    calendar = Calendar.from_ical(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-event-3
DTSTART;TZID=Eastern Standard Time:20260103T090000
EXDATE;TZID=Eastern Standard Time:20260104T090000,20260105T090000
RDATE;TZID=Eastern Standard Time:20260106T090000,20260107T090000
END:VEVENT
END:VCALENDAR
""",
    )

    normalized_calendar = normalize_tzids(calendar)
    event = normalized_calendar.walk("VEVENT")[0]

    assert event.get("EXDATE").params["TZID"] == "America/New_York"
    assert event.get("RDATE").params["TZID"] == "America/New_York"


def test_normalize_tzids_deduplicates_vtimezone_components_after_rename() -> None:
    calendar = Calendar()

    windows_vtimezone = Timezone()
    windows_vtimezone.add("TZID", "Eastern Standard Time")
    calendar.add_component(windows_vtimezone)

    iana_vtimezone = Timezone()
    iana_vtimezone.add("TZID", "America/New_York")
    calendar.add_component(iana_vtimezone)

    normalized_calendar = normalize_tzids(calendar)
    vtimezones = [
        component
        for component in normalized_calendar.subcomponents
        if component.name == "VTIMEZONE"
    ]

    assert len(vtimezones) == 1
    assert str(vtimezones[0].get("TZID")) == "America/New_York"


def test_normalize_tzids_noop_when_no_tzids_present() -> None:
    calendar = Calendar.from_ical(
        """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:test-event-4
DTSTART:20260108T090000Z
END:VEVENT
END:VCALENDAR
""",
    )
    original = calendar.to_ical()

    normalized_calendar = normalize_tzids(calendar)

    assert normalized_calendar.to_ical() == original
