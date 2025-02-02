import logging

import x_wr_timezone
from icalendar import Calendar as ICalendar
from icalendar import Event
from requests.exceptions import RequestException

from mergecalweb.calendars.calendar_fetcher import CalendarFetcher
from mergecalweb.calendars.models import Source
from mergecalweb.core.utils import is_local_url

from .source_data import SourceData

logger = logging.getLogger(__name__)


class LocalUrlError(Exception):
    pass


class SourceProcessor:
    def __init__(self, source: Source) -> None:
        self.source = source
        self.fetcher = CalendarFetcher()

    def process(self) -> SourceData:
        """Process a single source and return processed data"""
        source_data = SourceData(source=self.source)

        if is_local_url(self.source.url):
            msg = f"Local URL {self.source.url} is not allowed."
            raise LocalUrlError(msg)

        try:
            ical = self._fetch_and_validate()
            if ical:
                ical = self.customize_calendar(ical)
                source_data.ical = ical
        except (RequestException, ValueError) as e:
            source_data.error = str(e)
            logger.warning("Error processing source %s: %s", self.source.name, str(e))

        return source_data

    def _fetch_and_validate(self) -> ICalendar | None:
        """Fetch and validate remote calendar"""
        calendar_data = self.fetcher.fetch_calendar(self.source.url)
        ical = ICalendar.from_ical(calendar_data)

        if not ical.walk():
            msg = f"Calendar from {self.source.url} contains no components"
            raise ValueError(msg)

        return x_wr_timezone.to_standard(ical)

    def customize_calendar(self, ical: ICalendar) -> ICalendar:
        """Apply source-specific customizations to calendar"""
        if not self.source.calendar.owner.can_customize_sources:
            return ical

        for event in ical.walk("VEVENT"):
            if not self.source.include_title:
                event["summary"] = self.source.custom_prefix or self.source.name
            elif self.source.custom_prefix:
                event["summary"] = (
                    f"{self.source.custom_prefix}: {event.get('summary')}"
                )

            if not self.source.include_description:
                event.pop("description", None)

            if not self.source.include_location:
                event.pop("location", None)
            if self.source.calendar.show_branding:
                self._add_branding(event)

        return ical

    def _add_branding(self, event: Event):
        branding = "\n\nThis event is powered by MergeCal \nhttps://mergecal.org"
        description = event.get("description", "")
        event["description"] = description + branding
        summary = event.get("summary", "")
        event["summary"] = summary + " (via MergeCal.org)"
