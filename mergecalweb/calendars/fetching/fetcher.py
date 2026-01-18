import logging
import time
from datetime import timedelta
from urllib.parse import urlparse

import requests
from django.core.cache import cache

from mergecalweb.calendars.fetching.domain_configs import get_domain_config
from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = timedelta(minutes=2)  # Freshness threshold
MAX_STALE_AGE = timedelta(days=7)  # Maximum age to keep stale cache data
DEFAULT_TIMEOUT = 30


class CalendarFetcher:
    def fetch_calendar(self, url: str, timeout: int | None = None) -> str:
        """
        Fetch calendar data from URL with stale-while-revalidate caching.

        This implements a resilient caching strategy:
        - If cache is fresh (< 2 minutes): return immediately
        - If cache is stale but < 7 days old: try to refetch,
          fall back to stale on error
        - If cache is too old or missing: fetch fresh data

        Args:
            url: Calendar URL to fetch
            timeout: Request timeout in seconds (defaults to 30)

        Returns:
            Calendar data as string

        Raises:
            requests.RequestException: If fetch fails and no stale cache available
        """
        cache_key = f"calendar_data_{url}"
        cached_data = cache.get(cache_key)

        if cached_data is not None:
            # Unpack cached data (content, timestamp) or handle legacy format
            if isinstance(cached_data, tuple) and len(cached_data) == 2:  # noqa: PLR2004
                content, cached_at = cached_data
            else:
                # Legacy cache format (just string) - treat as stale and refetch
                content = cached_data
                cached_at = 0  # Force refresh by setting to epoch

            age_seconds = time.time() - cached_at

            if age_seconds < CACHE_TIMEOUT.total_seconds():
                # Cache is fresh - return immediately
                logger.debug(
                    "Calendar fetch cache hit (fresh)",
                    extra={
                        "event": LogEvent.CALENDAR_FETCH,
                        "status": "cache-hit-fresh",
                        "url": url[:200],
                        "size_bytes": len(content),
                        "age_seconds": round(age_seconds, 2),
                    },
                )
                return content

            if age_seconds < MAX_STALE_AGE.total_seconds():
                # Cache is stale but usable - try to refetch, fall back on error
                logger.debug(
                    "Calendar fetch cache hit (stale), attempting refresh",
                    extra={
                        "event": LogEvent.CALENDAR_FETCH,
                        "status": "cache-hit-stale",
                        "url": url[:200],
                        "age_seconds": round(age_seconds, 2),
                    },
                )
                try:
                    fresh_content = self._fetch_from_remote(url, timeout)
                    self._cache_content(cache_key, fresh_content)
                except requests.RequestException as e:
                    # Network/timeout error - fall back to stale cached content
                    logger.warning(
                        "Calendar fetch failed, using stale cache",
                        extra={
                            "event": LogEvent.CALENDAR_FETCH,
                            "status": "fetch-failed-using-stale",
                            "url": url[:200],
                            "error": str(e),
                            "error_type": type(e).__name__,
                            "age_seconds": round(age_seconds, 2),
                            "size_bytes": len(content),
                        },
                    )
                    return content
                else:
                    return fresh_content

            # Cache is too old - must refetch (will raise on error)
            logger.debug(
                "Calendar fetch cache expired (too old)",
                extra={
                    "event": LogEvent.CALENDAR_FETCH,
                    "status": "cache-expired",
                    "url": url[:200],
                    "age_seconds": round(age_seconds, 2),
                },
            )
            fresh_content = self._fetch_from_remote(url, timeout)
            self._cache_content(cache_key, fresh_content)
            return fresh_content

        # No cache - fetch fresh
        logger.debug(
            "Calendar fetch cache miss, fetching from remote",
            extra={
                "event": LogEvent.CALENDAR_FETCH,
                "status": "cache-miss",
                "url": url[:200],
            },
        )
        fresh_content = self._fetch_from_remote(url, timeout)
        self._cache_content(cache_key, fresh_content)
        return fresh_content

    def _fetch_from_remote(self, url: str, timeout: int | None = None) -> str:
        """
        Fetch calendar data from remote URL.

        Args:
            url: Calendar URL to fetch
            timeout: Request timeout in seconds

        Returns:
            Calendar data as string

        Raises:
            requests.RequestException: If fetch fails
        """
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
            return calendar_data  # noqa: TRY300
        except requests.RequestException as e:
            raise e from None

    def _cache_content(self, cache_key: str, content: str) -> None:
        """
        Cache calendar content with current timestamp.

        Args:
            cache_key: Cache key to use
            content: Calendar data to cache
        """
        # Store tuple of (content, timestamp) with long TTL
        # The long TTL keeps stale data available as fallback
        cached_value = (content, time.time())
        cache.set(cache_key, cached_value, MAX_STALE_AGE.total_seconds())

        logger.debug(
            "Calendar data cached with timestamp",
            extra={
                "event": LogEvent.CALENDAR_FETCH,
                "status": "cached",
                "cache_key": cache_key,
                "ttl_seconds": MAX_STALE_AGE.total_seconds(),
                "size_bytes": len(content),
            },
        )
