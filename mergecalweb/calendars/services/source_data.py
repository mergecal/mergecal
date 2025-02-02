from dataclasses import dataclass

from icalendar import Calendar as ICalendar

from mergecalweb.calendars.models import Source


@dataclass
class SourceData:
    source: Source
    ical: ICalendar | None = None
    error: str | None = None
