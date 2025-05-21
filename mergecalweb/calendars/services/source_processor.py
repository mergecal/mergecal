import contextlib
import logging
from typing import Final
from zoneinfo import ZoneInfoNotFoundError

import x_wr_timezone
from icalendar import Calendar as ICalendar
from icalendar import Event
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from mergecalweb.calendars.calendar_fetcher import CalendarFetcher
from mergecalweb.calendars.exceptions import CalendarValidationError
from mergecalweb.calendars.exceptions import CustomizationWithoutCalendarError
from mergecalweb.calendars.models import Source

from .source_data import SourceData

logger = logging.getLogger(__name__)


class SourceProcessor:
    BRANDING_URL: Final[str] = "https://mergecal.org"
    BRANDING_TEXT: Final[str] = "This event is powered by MergeCal"
    BRANDING_SUFFIX: Final[str] = "(via MergeCal.org)"

    def __init__(self, source: Source) -> None:
        self.source: Final[Source] = source
        self.fetcher: Final[CalendarFetcher] = CalendarFetcher()
        self.source_data: Final[SourceData] = SourceData(source=self.source)

    def fetch_and_validate(self) -> None:
        """Fetch and validate remote calendar."""
        try:
            calendar_data = self.fetcher.fetch_calendar(self.source.url)
            ical = self._validate_calendar_components(calendar_data)
            with contextlib.suppress(KeyError):
                ical.add_missing_timezones()
            try:
                self.source_data.ical = x_wr_timezone.to_standard(ical)
            except (AttributeError, ZoneInfoNotFoundError):
                # skip do to bug in x_wr_timezone
                # https://github.com/niccokunzmann/x-wr-timezone/issues/25
                self.source_data.ical = ical

        except (RequestException, HTTPError) as e:
            self.source_data.error = str(e)
        except CalendarValidationError as e:
            self.source_data.error = str(e)

    def _validate_calendar_components(self, calendar_data: str) -> ICalendar:
        """Validate calendar components."""
        try:
            ical = ICalendar.from_ical(calendar_data)
        except ValueError as e:
            msg = f'URL did not return valid ICalendar data.\nError Message: "{e}"'
            raise CalendarValidationError(msg) from e

        if not ical.walk():
            msg = "Calendar contains no components"
            raise CalendarValidationError(msg)

        # TODO: Explore other type of calendar validation
        return ical

    def customize_calendar(self) -> None:
        """Apply source-specific customizations to calendar"""
        if not self.source_data.ical:
            raise CustomizationWithoutCalendarError

        ical = self.source_data.ical
        owner_can_customize: bool = self.source.calendar.owner.can_customize_sources
        if not owner_can_customize:
            return

        for event in ical.walk("VEVENT"):
            if not self._should_include_event(event):
                ical.subcomponents.remove(event)
                continue
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

    def _add_branding(self, event: Event) -> None:
        """Add branding to event description and summary."""
        description: str = event.get("description", "")
        summary: str = event.get("summary", "")

        event["description"] = (
            f"{description}\n\n{self.BRANDING_TEXT} \n{self.BRANDING_URL}"
        )
        event["summary"] = f"{summary} {self.BRANDING_SUFFIX}"

    def _should_include_event(self, event: Event) -> bool:
        source = self.source
        calendar = source.calendar
        if not calendar.owner.can_customize_sources or not source.exclude_keywords:
            return True

        exclude_keywords = [
            kw.strip().lower() for kw in source.exclude_keywords.split(",")
        ]
        event_title = event.get("summary", "").lower()
        return not any(kw in event_title for kw in exclude_keywords)
