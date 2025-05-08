import logging
from typing import Final

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
            ical = ICalendar.from_ical(calendar_data)
            self._validate_calendar_components(ical)
            ical.add_missing_timezones()
            try:
                self.source_data.ical = x_wr_timezone.to_standard(ical)
            except AttributeError:
                # skip do to bug in x_wr_timezone
                # https://github.com/niccokunzmann/x-wr-timezone/issues/25
                self.source_data.ical = ical

        except (RequestException, HTTPError) as e:
            logger.warning("Failed to fetch calendar %s: %s", self.source.url, str(e))
            self.source_data.error = str(e)
        except CalendarValidationError as e:
            logger.warning(
                "Calendar validation failed for %s: %s",
                self.source.url,
                str(e),
            )
            self.source_data.error = str(e)
        except ValueError as e:
            logger.warning("Invalid calendar data from %s: %s", self.source.url, str(e))
            self.source_data.error = str(e)

    def _validate_calendar_components(self, ical: ICalendar) -> None:
        """Validate calendar components."""
        if not ical.walk():
            msg = f"Calendar from {self.source.url} contains no components"
            raise CalendarValidationError(msg)

        # TODO: Explore other type of calendar validation

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
