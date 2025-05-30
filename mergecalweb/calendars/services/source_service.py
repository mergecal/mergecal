# ruff: noqa: SLF001
import logging

from icalendar import Calendar as ICalendar
from requests.exceptions import RequestException
from urllib3.exceptions import HTTPError

from mergecalweb.calendars.exceptions import CalendarValidationError
from mergecalweb.calendars.meetup import fetch_and_create_meetup_calendar
from mergecalweb.calendars.meetup import is_meetup_url
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.utils import is_local_url
from mergecalweb.core.utils import parse_calendar_uuid

from .source_data import SourceData
from .source_processor import SourceProcessor

logger = logging.getLogger(__name__)


class SourceService:
    def __init__(self, existing_uuids=None) -> None:
        if existing_uuids is None:
            self.processed_uuids: set[str] = set()
        else:
            self.processed_uuids = existing_uuids

    def process_sources(self, sources: list[Source]) -> list[SourceData]:
        """Process multiple sources, handling special source types"""
        processed_sources = []

        for source in sources:
            processor = SourceProcessor(source)

            if is_local_url(source.url):
                self._process_local_source(processor.source_data)
            elif is_meetup_url(source.url):
                try:
                    logger.debug("Processing Meetup source: %s", source.url)
                    calendar_data = processor.fetcher.fetch_calendar(source.url)
                    ical = processor._validate_calendar_components(calendar_data)
                    processor.source_data.ical = ical
                except (RequestException, HTTPError, CalendarValidationError) as e:
                    logger.debug("using api to fetch meetup calendar: %s", e)
                    self._process_meetup_source(processor.source_data)

            else:
                processor.fetch_and_validate()

            if processor.source_data.ical:
                processor.customize_calendar()
            processed_sources.append(processor.source_data)

        return processed_sources

    def _process_local_source(self, source_data: SourceData) -> None:
        """Process a local source by using CalendarMergerService"""
        source = source_data.source
        uuid = parse_calendar_uuid(source.url)
        if not uuid:
            source_data.error = "Invalid local URL format"
            return

        if uuid in self.processed_uuids:
            source_data.error = "Circular calendar reference detected"
            return

        sub_calendar = Calendar.objects.filter(uuid=uuid).first()
        if not sub_calendar:
            source_data.error = "Referenced calendar does not exist"

        self.processed_uuids.add(uuid)

        # Import here to avoid circular imports
        from .calendar_merger_service import CalendarMergerService

        merger = CalendarMergerService(sub_calendar, self.processed_uuids)
        calendar_str = merger.merge()
        source_data.ical = ICalendar.from_ical(calendar_str)

    def _process_meetup_source(self, source_data: SourceData) -> None:
        """Process a Meetup source"""
        source = source_data.source
        ical = fetch_and_create_meetup_calendar(source.url)
        if not ical:
            logger.error("Failed to fetch Meetup calendar: %s", source.url)
            source_data.error = "Failed to fetch Meetup calendar"
            return

        source_data.ical = ical
