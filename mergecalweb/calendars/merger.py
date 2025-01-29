import logging
from datetime import timedelta

import httpx
from django.core.cache import cache
from icalendar import Calendar as ICalendar

from mergecalweb.calendars.models import Source

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = timedelta(minutes=2)


class SoucreService:
    def __init__(self, source: Source):
        self.source: Source = source
        self.url: str = source.url
        self.calendar = None | ICalendar
        self.raw_calendar_text: str = ""

    def _fetch_calendar(self) -> None:
        url = self.url
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

        response = httpx.get(url, headers=headers)
        response.encoding = "utf-8"
        response.raise_for_status()
        calendar_data = response.text

        # Cache the raw calendar data
        cache.set(cache_key, calendar_data, CACHE_TIMEOUT.total_seconds())

        self.raw_calendar_text = calendar_data
        return None

    def _validate_calendar(self) -> None:
        self._fetch_calendar()
        self.calendar = ICalendar.from_ical(self.raw_calendar_text)
        if not self.calendar.walk():
            msg = f"Calendar from {self.url} contains no components"
            raise ValueError(msg)

    def _apply_custom_rules(self):
        self._fetch_calendar()

    def run(self):
        self._apply_custom_rules()
