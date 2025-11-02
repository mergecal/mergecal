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
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.core.utils import is_local_url
from mergecalweb.core.utils import parse_calendar_uuid

from .source_data import SourceData
from .source_processor import SourceProcessor

logger = logging.getLogger(__name__)

# Timeout constants
MAX_REQUEST_TIMEOUT = 60  # 1 minute max for the entire request
MIN_PER_SOURCE_TIMEOUT = 5  # Minimum timeout per source in seconds
SAFETY_BUFFER = 5  # Safety buffer in seconds to complete before gunicorn timeout


class SourceService:
    def __init__(self, existing_uuids=None) -> None:
        if existing_uuids is None:
            self.processed_uuids: set[str] = set()
        else:
            self.processed_uuids = existing_uuids

    def _calculate_per_source_timeout(self, source_count: int) -> int:
        """
        Calculate timeout per source based on total source count.

        With a 60-second Gunicorn timeout, we need to ensure all sources
        can be fetched within that time. We distribute the available time
        across all sources, with a minimum timeout per source.

        Note: If there are many sources (>11), each source will get the
        minimum timeout (5s), which may cause the total time to exceed
        the Gunicorn timeout. In this case, some sources may fail due to
        the overall request timeout, and the request should be moved to
        a background task.

        Args:
            source_count: Total number of sources to fetch

        Returns:
            Timeout in seconds per source
        """
        if source_count <= 0:
            return MIN_PER_SOURCE_TIMEOUT

        # Calculate available time after safety buffer
        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER

        # Distribute time across all sources
        per_source_timeout = available_time // source_count

        # Ensure we don't go below minimum timeout
        effective_timeout = max(per_source_timeout, MIN_PER_SOURCE_TIMEOUT)

        # Warn if total estimated time exceeds max timeout
        estimated_total_time = effective_timeout * source_count
        if estimated_total_time > MAX_REQUEST_TIMEOUT:
            logger.warning(
                "Estimated fetch time exceeds Gunicorn timeout limit",
                extra={
                    "event": LogEvent.SOURCE_TIMEOUT_CALCULATED,
                    "source_count": source_count,
                    "per_source_timeout_seconds": effective_timeout,
                    "estimated_total_seconds": estimated_total_time,
                    "max_request_timeout_seconds": MAX_REQUEST_TIMEOUT,
                    "warning": "Consider using background task for this calendar",
                },
            )
        else:
            logger.debug(
                "Calculated per-source timeout",
                extra={
                    "event": LogEvent.SOURCE_TIMEOUT_CALCULATED,
                    "source_count": source_count,
                    "available_time_seconds": available_time,
                    "per_source_timeout_seconds": effective_timeout,
                    "estimated_total_seconds": estimated_total_time,
                    "max_request_timeout_seconds": MAX_REQUEST_TIMEOUT,
                },
            )

        return effective_timeout

    def process_sources(self, sources: list[Source]) -> list[SourceData]:
        """Process multiple sources, handling special source types"""
        processed_sources = []

        # Calculate timeout based on source count
        source_count = len(sources)
        per_source_timeout = self._calculate_per_source_timeout(source_count)

        for source in sources:
            processor = SourceProcessor(source, timeout=per_source_timeout)

            if is_local_url(source.url):
                self._process_local_source(processor.source_data)
            elif is_meetup_url(source.url):
                try:
                    logger.debug("Processing Meetup source: %s", source.url)
                    calendar_data = processor.fetcher.fetch_calendar(
                        source.url,
                        timeout=per_source_timeout,
                    )
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

        logger.debug(
            "Processing local source: source=%s, url=%s, parsed_uuid=%s",
            source.name,
            source.url,
            uuid,
        )

        if not uuid:
            source_data.error = "Invalid local URL format"
            logger.error(
                "Local source: Invalid URL format",
                extra={
                    "event": LogEvent.SOURCE_LOCAL_INVALID_FORMAT,
                    "source_id": source.pk,
                    "source_url": source.url,
                    "source_name": source.name,
                    "calendar_uuid": source.calendar.uuid,
                },
            )
            return

        if uuid in self.processed_uuids:
            source_data.error = "Circular calendar reference detected"
            logger.error(
                "Local source: Circular reference detected",
                extra={
                    "event": LogEvent.SOURCE_LOCAL_CIRCULAR_REF,
                    "source_id": source.pk,
                    "source_url": source.url,
                    "source_name": source.name,
                    "calendar_uuid": source.calendar.uuid,
                    "nested_uuid": uuid,
                },
            )
            return

        sub_calendar = Calendar.objects.filter(uuid=uuid).first()
        if not sub_calendar:
            source_data.error = "Referenced calendar does not exist"
            logger.error(
                "Local source: Calendar not found",
                extra={
                    "event": LogEvent.SOURCE_LOCAL_NOT_FOUND,
                    "source_id": source.pk,
                    "source_url": source.url,
                    "source_name": source.name,
                    "calendar_uuid": source.calendar.uuid,
                    "nested_uuid": uuid,
                },
            )
            return

        self.processed_uuids.add(uuid)

        # Import here to avoid circular imports
        from .calendar_merger_service import CalendarMergerService

        logger.info(
            "Local source: Merging nested calendar",
            extra={
                "event": LogEvent.SOURCE_LOCAL_MERGE_START,
                "source_id": source.pk,
                "source_name": source.name,
                "calendar_uuid": source.calendar.uuid,
                "nested_calendar_uuid": sub_calendar.uuid,
                "nested_calendar_name": sub_calendar.name,
            },
        )

        merger = CalendarMergerService(sub_calendar, self.processed_uuids)
        calendar_str = merger.merge()
        source_data.ical = ICalendar.from_ical(calendar_str)

        logger.info(
            "Local source: Nested calendar merged successfully",
            extra={
                "event": LogEvent.SOURCE_LOCAL_MERGE_SUCCESS,
                "source_id": source.pk,
                "source_name": source.name,
                "calendar_uuid": source.calendar.uuid,
                "nested_calendar_uuid": sub_calendar.uuid,
                "nested_calendar_name": sub_calendar.name,
            },
        )

    def _process_meetup_source(self, source_data: SourceData) -> None:
        """Process a Meetup source"""
        source = source_data.source
        ical = fetch_and_create_meetup_calendar(source.url)
        if not ical:
            logger.error(
                "Failed to fetch Meetup calendar",
                extra={
                    "event": LogEvent.SOURCE_MEETUP_FETCH_ERROR,
                    "source_id": source.pk,
                    "source_url": source.url,
                    "source_name": source.name,
                    "calendar_uuid": source.calendar.uuid,
                },
            )
            source_data.error = "Failed to fetch Meetup calendar"
            return

        source_data.ical = ical
