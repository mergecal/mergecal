# ruff: noqa: SLF001
import logging
import time

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

    def process_sources(self, sources: list[Source]) -> list[SourceData]:
        """Process multiple sources, handling special source types with dynamic timeout distribution"""
        processed_sources = []
        source_count = len(sources)

        # Track time for dynamic timeout redistribution
        start_time = time.time()
        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER

        # Warn if minimum timeout requirement exceeds available time
        minimum_required_time = source_count * MIN_PER_SOURCE_TIMEOUT
        if minimum_required_time > available_time:
            logger.warning(
                "Source count too high for available time budget",
                extra={
                    "event": LogEvent.SOURCE_FETCH,
                    "status": "timeout-warning",
                    "source_count": source_count,
                    "min_per_source_timeout_seconds": MIN_PER_SOURCE_TIMEOUT,
                    "minimum_required_seconds": minimum_required_time,
                    "available_time_seconds": available_time,
                    "max_request_timeout_seconds": MAX_REQUEST_TIMEOUT,
                    "warning": "Consider using background task for this calendar",
                },
            )

        for idx, source in enumerate(sources):
            # Calculate dynamic timeout based on remaining time and sources
            elapsed_time = time.time() - start_time
            remaining_time = available_time - elapsed_time
            remaining_sources = source_count - idx

            # Distribute remaining time across remaining sources
            if remaining_sources > 0 and remaining_time > 0:
                per_source_timeout = max(
                    int(remaining_time / remaining_sources),
                    MIN_PER_SOURCE_TIMEOUT,
                )
            else:
                # Fallback to minimum timeout if we're running out of time
                per_source_timeout = MIN_PER_SOURCE_TIMEOUT

            logger.debug(
                "Dynamic timeout calculated for source",
                extra={
                    "event": LogEvent.SOURCE_FETCH,
                    "status": "timeout-calculated",
                    "source_index": idx,
                    "source_id": source.pk,
                    "source_name": source.name,
                    "elapsed_seconds": round(elapsed_time, 2),
                    "remaining_seconds": round(remaining_time, 2),
                    "remaining_sources": remaining_sources,
                    "per_source_timeout_seconds": per_source_timeout,
                },
            )

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

        # Log final statistics
        total_elapsed = time.time() - start_time
        logger.info(
            "Completed processing all sources",
            extra={
                "event": LogEvent.SOURCE_FETCH,
                "status": "completed",
                "source_count": source_count,
                "total_elapsed_seconds": round(total_elapsed, 2),
                "available_time_seconds": available_time,
                "time_saved_seconds": round(available_time - total_elapsed, 2),
            },
        )

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
                    "event": LogEvent.SOURCE_ERROR,
                    "error_type": "invalid-format",
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
                    "event": LogEvent.SOURCE_ERROR,
                    "error_type": "circular-ref",
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
                    "event": LogEvent.SOURCE_ERROR,
                    "error_type": "not-found",
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
        from .calendar_merger_service import CalendarMergerService  # noqa: PLC0415

        logger.info(
            "Local source: Merging nested calendar",
            extra={
                "event": LogEvent.SOURCE_FETCH,
                "status": "start",
                "source_type": "local",
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
                "event": LogEvent.SOURCE_FETCH,
                "status": "success",
                "source_type": "local",
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
                    "event": LogEvent.SOURCE_FETCH,
                    "status": "failed",
                    "source_type": "meetup",
                    "source_id": source.pk,
                    "source_url": source.url,
                    "source_name": source.name,
                    "calendar_uuid": source.calendar.uuid,
                },
            )
            source_data.error = "Failed to fetch Meetup calendar"
            return

        source_data.ical = ical
