import logging
from uuid import UUID

from django.core.cache import cache

from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)


def calendar_output_cache_key(uuid: UUID | str) -> str:
    return f"calendar_str_{uuid}"


def source_data_cache_key(url: str) -> str:
    return f"calendar_data_{url}"


def invalidate_calendar_cache(calendar) -> None:
    keys = [calendar_output_cache_key(calendar.uuid)]
    keys.extend(
        source_data_cache_key(source.url) for source in calendar.calendarOf.all()
    )
    cache.delete_many(keys)
    logger.info(
        "Cache invalidated",
        extra={
            "event": LogEvent.CACHE_INVALIDATED,
            "calendar_uuid": calendar.uuid,
            "calendar_name": calendar.name,
        },
    )
