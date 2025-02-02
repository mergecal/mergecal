import logging
from datetime import timedelta
from typing import Final

from django.core.cache import cache
from django.utils import timezone
from icalendar import Alarm
from icalendar import Calendar as ICalendar
from icalendar import Event
from mergecal import CalendarMerger

from mergecalweb.calendars.models import Calendar

from .source_data import SourceData
from .source_service import SourceService

logger = logging.getLogger(__name__)


class CalendarMergerService:
    def __init__(
        self,
        calendar: Calendar,
        existing_uuids: set[str] | None = None,
    ) -> None:
        self.calendar: Final[Calendar] = calendar
        self.existing_uuids: Final[set[str] | None] = existing_uuids

    def merge(self) -> str:
        """Merge all calendar sources into a single iCal string"""
        cache_key = f"calendar_str_{self.calendar.uuid}"
        cached_calendar = cache.get(cache_key)

        if cached_calendar is not None:
            return cached_calendar

        processed_sources: list[SourceData] = self._process_sources()
        valid_calendars: list[ICalendar] = [
            s.ical for s in processed_sources if s.ical is not None
        ]

        merged_calendar: ICalendar = self._merge_calendars(valid_calendars)
        self._add_error_events(merged_calendar, processed_sources)
        self._add_tier_warnings(merged_calendar)

        calendar_str = merged_calendar.to_ical().decode("utf-8")
        cache.set(cache_key, calendar_str, self.calendar.effective_update_frequency)

        return calendar_str

    def _process_sources(self) -> list[SourceData]:
        """Process all calendar sources"""
        sources = self.calendar.calendarOf.all()
        source_service = SourceService(self.existing_uuids)
        return source_service.process_sources(sources)

    def _merge_calendars(self, calendars: list[ICalendar]) -> ICalendar:
        prodid = f"-//{self.calendar.name}//mergecal.org//"
        version = "2.0"
        if len(calendars) == 0:
            # TODO: need to return a valid calendar with at least one component
            calendar = ICalendar()
            calendar.add("prodid", prodid)
            calendar.add("version", version)
            calendar.add("x-wr-calname", self.calendar.name)
            return calendar

        """Merge calendars using CalendarMerger with appropriate settings."""
        merger = CalendarMerger(
            calendars,
            prodid=prodid,
            version=version,
        )
        icalendar: ICalendar = merger.merge()
        icalendar.add("x-wr-calname", self.calendar.name)

        existing_tzids = set()
        for cal in calendars:
            for component in cal.walk("VTIMEZONE"):
                tzid = component.get("tzid")
                if tzid in existing_tzids:
                    continue
                existing_tzids.add(tzid)
                icalendar.add_component(component)

        return icalendar

    def _add_error_events(
        self,
        merged_calendar: ICalendar,
        processed_sources: list[SourceData],
    ) -> None:
        """Add error events for sources that failed to process"""
        error_sources = [s for s in processed_sources if s.error is not None]
        if not error_sources:
            return

        error_event = Event()
        error_event.add("summary", "MergeCal: Source Errors")
        error_description = "The following sources had errors:\n\n"

        for source_data in error_sources:
            error_description += (
                f"- {source_data.source.name} "
                f"({source_data.source.url}): {source_data.error}\n"
            )

        error_event.add("description", error_description)
        error_event.add("dtstart", timezone.now())
        error_event.add("dtend", timezone.now() + timedelta(hours=1))
        merged_calendar.add_component(error_event)

    def _add_tier_warnings(self, merged_calendar: ICalendar) -> None:
        """Add warning events for free tier users"""
        if not self.calendar.owner.is_free_tier:
            return

        warning_event = Event()
        start_time = timezone.now()

        warning_event.add(
            "summary",
            "⚠️ Action Required: Your MergeCal Access Will Be Discontinued",
        )
        description = (
            "⚠️ Your MergeCal calendar access will be discontinued soon.\n\n"
            "🎁 Get 1 Month FREE on our Business Plan with code: FREEMONTH\n\n"
            "Subscribe now to keep your calendars synchronized:\n"
            "https://mergecal.org/pricing/"
        )

        warning_event.add("description", description)
        warning_event.add("dtstart", start_time)
        warning_event.add("dtend", start_time + timedelta(hours=24))
        warning_event.add("priority", 1)
        warning_event.add("uid", f"access-warning-{self.calendar.uuid}")

        # Add alarm
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add(
            "description",
            "Your MergeCal access will be discontinued. Subscribe to our Business Plan - "  # noqa: E501
            "1 Month FREE with code: FREEMONTH",
        )
        alarm.add("trigger", timedelta(hours=3))
        warning_event.add_component(alarm)

        merged_calendar.add_component(warning_event)
