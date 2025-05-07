# calendar_fetcher.py

import logging
from datetime import timedelta

import requests
from django.core.cache import cache
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# CACHE_TIMEOUT = timedelta(minutes=2)
CACHE_TIMEOUT = timedelta(seconds=2)
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
        cache_key = f"calendar_data_{url}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.debug("Calendar data found in cache for URL: %s", cache_key)
            return cached_data

        logger.debug("Fetching calendar data for URL: %s", url)
        headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }

        response = self.session.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        response.encoding = "utf-8"
        response.raise_for_status()
        calendar_data = response.text

        # Cache the raw calendar data
        cache.set(cache_key, calendar_data, CACHE_TIMEOUT.total_seconds())

        return calendar_data
