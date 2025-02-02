import logging

from icalendar import Calendar as ICalendar

from mergecalweb.calendars.meetup import fetch_and_create_meetup_calendar
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.utils import is_local_url
from mergecalweb.core.utils import parse_calendar_uuid

from .source_data import SourceData
from .source_processor import SourceProcessor

logger = logging.getLogger(__name__)


class SourceService:
    def __init__(self) -> None:
        self.processed_uuids: set[str] = set()

    def process_sources(self, sources: list[Source]) -> list[SourceData]:
        """Process multiple sources, handling special source types"""
        processed_sources = []

        for source in sources:
            if is_local_url(source.url):
                source_data = self._process_local_source(source)
            elif "meetup.com" in source.url:
                source_data = self._process_meetup_source(source)
            else:
                source_data = SourceProcessor(source).process()

            processed_sources.append(source_data)

        return processed_sources

    def _process_local_source(self, source: Source) -> SourceData:
        """Process a local source by using CalendarMergerService"""
        uuid = parse_calendar_uuid(source.url)
        if not uuid:
            return SourceData(source=source, error="Invalid local URL format")

        if uuid in self.processed_uuids:
            return SourceData(
                source=source,
                error="Circular calendar reference detected",
            )

        sub_calendar = Calendar.objects.filter(uuid=uuid).first()
        if not sub_calendar:
            return SourceData(source=source, error="Referenced calendar does not exist")

        self.processed_uuids.add(uuid)

        # Import here to avoid circular imports
        from .calendar_merger_service import CalendarMergerService

        merger = CalendarMergerService(sub_calendar)
        calendar_str = merger.merge()
        ical = ICalendar.from_ical(calendar_str)

        # Apply parent source's customizations
        processor = SourceProcessor(source)
        ical = processor.customize_calendar(ical)

        return SourceData(source=source, ical=ical)

    def _process_meetup_source(self, source: Source) -> SourceData:
        """Process a Meetup source"""
        ical = fetch_and_create_meetup_calendar(source.url)
        if not ical:
            logger.error("Failed to fetch Meetup calendar: %s", source.url)
            return SourceData(source=source, error="Failed to fetch Meetup calendar")

        processor = SourceProcessor(source)
        ical = processor.customize_calendar(ical)

        return SourceData(source=source, ical=ical)
