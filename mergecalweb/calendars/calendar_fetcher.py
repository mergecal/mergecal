# calendar_fetcher.py
import logging
import time
from datetime import timedelta

import requests
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = timedelta(minutes=2)
DEFAULT_TIMEOUT = 30  # seconds


class CalendarFetcher:
    def __init__(self):
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def fetch_calendar(self, url: str, timeout: int | None = None) -> str:
        """
        Fetches calendar data from the given URL.

        Args:
            url: The URL to fetch calendar data from.
            timeout: Optional timeout in seconds. If not provided, uses DEFAULT_TIMEOUT.

        Returns:
            Tuple[str, None]: A tuple containing the calendar data as a string and None.
                              If an error occurs, returns (None, error_message).
        """
        cache_key = f"calendar_data_{url}"
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
            response = self.session.get(url, headers=headers, timeout=effective_timeout)
            response.encoding = "utf-8"
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

            # Cache the raw calendar data
            cache.set(cache_key, calendar_data, CACHE_TIMEOUT.total_seconds())
            logger.debug(
                "Calendar data cached",
                extra={
                    "event": LogEvent.CALENDAR_FETCH_CACHED,
                    "cache_key": cache_key[:200],
                    "ttl_seconds": CACHE_TIMEOUT.total_seconds(),
                    "size_bytes": len(calendar_data),
                },
            )
            return calendar_data  # noqa: TRY300

        except Exception as e:
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
