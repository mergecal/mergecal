import hashlib
import logging
import time
from datetime import timedelta

import requests
from django.core.cache import cache

from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = timedelta(minutes=2)
DEFAULT_TIMEOUT = 30

_shared_session = None


def get_session() -> requests.Session:
    global _shared_session  # noqa: PLW0603
    if _shared_session is None:
        _shared_session = requests.Session()
    return _shared_session


class CalendarFetcher:
    def __init__(self):
        self.session = get_session()

    def fetch_calendar(self, url: str, timeout: int | None = None) -> str:
        cache_key = f"cal_{hashlib.sha256(url.encode()).hexdigest()[:16]}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.debug(
                "Calendar fetch cache hit",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_CACHE_HIT,
                    "url": url[:200],
                    "size_bytes": len(cached_data),
                },
            )
            return cached_data

        logger.debug(
            "Calendar fetch cache miss, fetching from remote",
            extra={
                "event": LogEvent.CALENDAR_FETCH_CACHE_MISS,
                "url": url[:200],
            },
        )
        start_time = time.time()

        headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }

        effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

        try:
            response = self.session.get(
                url,
                headers=headers,
                timeout=effective_timeout,
            )
            response.raise_for_status()
            calendar_data = response.text

            fetch_duration = time.time() - start_time
            logger.debug(
                "Calendar fetched successfully from remote source",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_SUCCESS,
                    "url": url[:200],
                    "status_code": response.status_code,
                    "size_bytes": len(calendar_data),
                    "duration_seconds": round(fetch_duration, 2),
                },
            )

            cache.set(cache_key, calendar_data, CACHE_TIMEOUT.total_seconds())
            logger.debug(
                "Calendar data cached",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_CACHED,
                    "cache_key": cache_key,
                    "ttl_seconds": CACHE_TIMEOUT.total_seconds(),
                    "size_bytes": len(calendar_data),
                },
            )
            return calendar_data  # noqa: TRY300
        except (requests.Timeout, requests.ConnectionError) as e:
            fetch_duration = time.time() - start_time
            logger.warning(
                "Calendar fetch failed due to network timeout or connection error",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_FAILED,
                    "url": url[:200],
                    "error_type": type(e).__name__,
                    "duration_seconds": round(fetch_duration, 2),
                },
            )
            raise
        except requests.RequestException as e:
            fetch_duration = time.time() - start_time
            logger.exception(
                "Calendar fetch failed from remote source",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_FAILED,
                    "url": url[:200],
                    "error_type": type(e).__name__,
                    "duration_seconds": round(fetch_duration, 2),
                },
            )
            raise
