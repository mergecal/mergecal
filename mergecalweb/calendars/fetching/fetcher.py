import logging
import time
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.core.cache import cache

from mergecalweb.calendars.fetching.domain_configs import get_domain_config
from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = timedelta(minutes=2)
DEFAULT_TIMEOUT = 30


class CalendarFetcher:
    def fetch_calendar(self, url: str, timeout: int | None = None) -> str:
        cache_key = f"calendar_data_{url}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            logger.debug(
                "Calendar fetch cache hit",
                extra={
                    "event": LogEvent.CALENDAR_FETCH,
                    "status": "cache-hit",
                    "url": url[:200],
                    "size_bytes": len(cached_data),
                },
            )
            return cached_data

        logger.debug(
            "Calendar fetch cache miss, fetching from remote",
            extra={
                "event": LogEvent.CALENDAR_FETCH,
                "status": "cache-miss",
                "url": url[:200],
            },
        )
        start_time = time.time()

        # Get domain-specific configuration if available
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        domain_config = get_domain_config(domain)

        # Build headers with domain-specific overrides
        headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }

        # Apply domain-specific overrides
        if domain_config:
            if "user_agent" in domain_config:
                headers["User-Agent"] = domain_config["user_agent"]
            if "accept" in domain_config:
                headers["Accept"] = domain_config["accept"]
            if "additional_headers" in domain_config:
                headers.update(domain_config["additional_headers"])

            logger.debug(
                "Applied domain-specific calendar fetch configuration",
                extra={
                    "event": LogEvent.CALENDAR_FETCH,
                    "status": "domain-config",
                    "domain": domain,
                    "has_custom_ua": "user_agent" in domain_config,
                    "has_custom_accept": "accept" in domain_config,
                },
            )

        effective_timeout = timeout if timeout is not None else DEFAULT_TIMEOUT

        try:
            response = requests.get(
                url,
                headers=headers,
                timeout=effective_timeout,
            )
            response.raise_for_status()
            response.encoding = "utf-8"
            calendar_data = response.text

            fetch_duration = time.time() - start_time
            logger.debug(
                "Calendar fetched successfully from remote source",
                extra={
                    "event": LogEvent.CALENDAR_FETCH,
                    "status": "success",
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
                    "event": LogEvent.CALENDAR_FETCH,
                    "status": "cached",
                    "cache_key": cache_key,
                    "ttl_seconds": CACHE_TIMEOUT.total_seconds(),
                    "size_bytes": len(calendar_data),
                },
            )
            return calendar_data  # noqa: TRY300
        except requests.RequestException as e:
            raise e from None
