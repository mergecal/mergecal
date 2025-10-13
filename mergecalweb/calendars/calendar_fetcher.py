# calendar_fetcher.py

import logging
from datetime import timedelta

import requests
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

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

    def fetch_calendar(self, url: str) -> str:
        """
        Fetches calendar data from the given URL.

        Returns:
            Tuple[str, None]: A tuple containing the calendar data as a string and None.
                              If an error occurs, returns (None, error_message).
        """
        import time

        cache_key = f"calendar_data_{url}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.info(
                "Calendar fetch: Cache HIT - url=%s, cache_key=%s, size=%d bytes",
                url,
                cache_key,
                len(cached_data),
            )
            return cached_data

        logger.info("Calendar fetch: Cache MISS - fetching from remote url=%s", url)
        start_time = time.time()

        headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }

        try:
            response = self.session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
            response.encoding = "utf-8"
            response.raise_for_status()
            calendar_data = response.text

            fetch_duration = time.time() - start_time
            logger.info(
                "Calendar fetch: SUCCESS - url=%s, status=%d, size=%d bytes, duration=%.2fs",  # noqa: E501
                url,
                response.status_code,
                len(calendar_data),
                fetch_duration,
            )

            # Cache the raw calendar data
            cache.set(cache_key, calendar_data, CACHE_TIMEOUT.total_seconds())
            logger.debug(
                "Calendar data cached: cache_key=%s, ttl=%ds",
                cache_key,
                CACHE_TIMEOUT.total_seconds(),
            )

        except Exception as e:
            fetch_duration = time.time() - start_time
            logger.exception(
                "Calendar fetch: FAILED - url=%s, error_type=%s, duration=%.2fs",
                url,
                type(e).__name__,
                fetch_duration,
            )
            raise
        else:
            return calendar_data
