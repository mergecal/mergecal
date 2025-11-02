import contextlib
import logging
from typing import Final
from zoneinfo import ZoneInfoNotFoundError

import requests
import x_wr_timezone
from icalendar import Calendar as ICalendar
from icalendar import Event
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from mergecalweb.calendars.exceptions import CalendarValidationError
from mergecalweb.calendars.exceptions import CustomizationWithoutCalendarError
from mergecalweb.calendars.fetching import CalendarFetcher
from mergecalweb.calendars.models import Source
from mergecalweb.core.logging_events import LogEvent

from .source_data import SourceData

logger = logging.getLogger(__name__)


class SourceProcessor:
    BRANDING_URL: Final[str] = "https://mergecal.org"
    BRANDING_TEXT: Final[str] = "This event is powered by MergeCal"
    BRANDING_SUFFIX: Final[str] = "(via MergeCal.org)"

    def __init__(self, source: Source, timeout: int | None = None) -> None:
        self.source: Final[Source] = source
        self.timeout: Final[int | None] = timeout
        self.fetcher: Final[CalendarFetcher] = CalendarFetcher()
        self.source_data: Final[SourceData] = SourceData(source=self.source)

    def fetch_and_validate(self) -> None:
        """Fetch and validate remote calendar."""
        logger.debug(
            "Starting source fetch and validation",
            extra={
                "event": LogEvent.SOURCE_FETCH_START,
                "source_id": self.source.pk,
                "source_name": self.source.name,
                "source_url": self.source.url[:200],
                "calendar_uuid": self.source.calendar.uuid,
            },
        )

        try:
            calendar_data = self.fetcher.fetch_calendar(
                self.source.url,
                timeout=self.timeout,
            )
            ical = self._validate_calendar_components(calendar_data)

            with contextlib.suppress(KeyError):
                ical.add_missing_timezones()

            try:
                self.source_data.ical = x_wr_timezone.to_standard(ical)
                logger.debug(
                    "Source timezone standardization successful",
                    extra={
                        "event": LogEvent.SOURCE_TIMEZONE_STANDARDIZED,
                        "source_id": self.source.pk,
                        "source_name": self.source.name,
                    },
                )
            except (AttributeError, ZoneInfoNotFoundError) as e:
                # skip do to bug in x_wr_timezone
                # https://github.com/niccokunzmann/x-wr-timezone/issues/25
                logger.warning(
                    "Source timezone standardization skipped due to error",
                    extra={
                        "event": LogEvent.SOURCE_TIMEZONE_SKIP,
                        "source_id": self.source.pk,
                        "source_name": self.source.name,
                        "error": str(e),
                    },
                )
                self.source_data.ical = ical

            logger.debug(
                "Source fetched and validated successfully",
                extra={
                    "event": LogEvent.SOURCE_FETCH_SUCCESS,
                    "source_id": self.source.pk,
                    "source_name": self.source.name,
                    "source_url": self.source.url[:200],
                    "calendar_uuid": self.source.calendar.uuid,
                },
            )

        except requests.Timeout as e:
            self.source_data.error = str(e)
            logger.info(
                "Source fetch timed out",
                extra={
                    "event": LogEvent.SOURCE_FETCH_TIMEOUT,
                    "source_id": self.source.pk,
                    "source_name": self.source.name,
                    "source_url": self.source.url[:200],
                    "calendar_uuid": self.source.calendar.uuid,
                    "timeout_seconds": self.timeout,
                },
            )
        except (RequestException, HTTPError) as e:
            self.source_data.error = str(e)
            logger.warning(
                "Source fetch failed due to network error",
                extra={
                    "event": LogEvent.SOURCE_FETCH_NETWORK_ERROR,
                    "source_id": self.source.pk,
                    "source_name": self.source.name,
                    "source_url": self.source.url[:200],
                    "calendar_uuid": self.source.calendar.uuid,
                    "error_type": type(e).__name__,
                },
            )
        except CalendarValidationError as e:
            self.source_data.error = str(e)
            logger.exception(
                "Source fetch failed due to validation error",
                extra={
                    "event": LogEvent.SOURCE_FETCH_VALIDATION_ERROR,
                    "source_id": self.source.pk,
                    "source_name": self.source.name,
                    "source_url": self.source.url[:200],
                    "calendar_uuid": self.source.calendar.uuid,
                    "error_message": str(e),
                },
            )

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

        logger.debug(
            "Starting source customization",
            extra={
                "event": LogEvent.SOURCE_CUSTOMIZATION_START,
                "source_id": self.source.pk,
                "source_name": self.source.name,
                "can_customize": owner_can_customize,
                "has_custom_prefix": bool(self.source.custom_prefix),
                "has_exclude_keywords": bool(self.source.exclude_keywords),
            },
        )

        if not owner_can_customize:
            logger.debug(
                "Source customization skipped, user lacks permission",
                extra={
                    "event": LogEvent.SOURCE_CUSTOMIZATION_SKIPPED,
                    "source_id": self.source.pk,
                    "source_name": self.source.name,
                    "owner_tier": self.source.calendar.owner.subscription_tier,
                },
            )
            return

        events_removed = 0
        events_customized = 0

        for event in ical.walk("VEVENT"):
            if not self._should_include_event(event):
                ical.subcomponents.remove(event)
                events_removed += 1
                continue

            if not self.source.include_title:
                event["summary"] = self.source.custom_prefix or self.source.name
                events_customized += 1
            elif self.source.custom_prefix:
                event["summary"] = (
                    f"{self.source.custom_prefix}: {event.get('summary')}"
                )
                events_customized += 1

            if not self.source.include_description:
                event.pop("description", None)
                events_customized += 1

            if not self.source.include_location:
                event.pop("location", None)
                events_customized += 1

            if self.source.calendar.show_branding:
                self._add_branding(event)
                events_customized += 1

        logger.debug(
            "Source customization completed",
            extra={
                "event": LogEvent.SOURCE_CUSTOMIZATION_COMPLETE,
                "source_id": self.source.pk,
                "source_name": self.source.name,
                "calendar_uuid": self.source.calendar.uuid,
                "events_removed": events_removed,
                "events_customized": events_customized,
            },
        )

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
