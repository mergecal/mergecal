import time
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests

from mergecalweb.calendars.fetching.fetcher import CACHE_TIMEOUT
from mergecalweb.calendars.fetching.fetcher import MAX_STALE_AGE
from mergecalweb.calendars.fetching.fetcher import CalendarFetcher


@pytest.fixture
def fetcher():
    return CalendarFetcher()


@pytest.fixture
def mock_cache():
    with patch("mergecalweb.calendars.fetching.fetcher.cache") as mock:
        yield mock


@pytest.fixture
def mock_requests():
    with patch("requests.get") as mock:
        yield mock


class TestCalendarFetcher:
    def test_fetch_fresh_cache_hit(self, fetcher, mock_cache):
        """Test that fresh cache returns immediately without network request"""
        url = "http://example.com/cal.ics"
        content = "CALENDAR DATA"
        # Cache set very recently
        cached_value = (content, time.time())

        mock_cache.get.return_value = cached_value

        with patch.object(fetcher, "_fetch_from_remote") as mock_fetch:
            result = fetcher.fetch_calendar(url)

            assert result == content
            mock_fetch.assert_not_called()

    def test_fetch_stale_cache_refresh_success(self, fetcher, mock_cache):
        """Test that stale cache triggers refresh and updates cache on success"""
        url = "http://example.com/cal.ics"
        old_content = "OLD DATA"
        new_content = "NEW DATA"
        # Cache set just over CACHE_TIMEOUT ago
        cache_time = time.time() - (CACHE_TIMEOUT.total_seconds() + 10)
        cached_value = (old_content, cache_time)

        mock_cache.get.return_value = cached_value

        with patch.object(
            fetcher,
            "_fetch_from_remote",
            return_value=new_content,
        ) as mock_fetch:
            # Should mock the cache.set call to verify it's updated
            result = fetcher.fetch_calendar(url)

            assert result == new_content
            mock_fetch.assert_called_once_with(url, None)

            # Verify cache update happened via _cache_content
            # We need to check what cache.set was called with
            assert mock_cache.set.called

    def test_fetch_stale_cache_refresh_failure(self, fetcher, mock_cache):
        """Test that stale cache is returned when refresh fails"""
        url = "http://example.com/cal.ics"
        old_content = "OLD DATA"
        # Cache set just over CACHE_TIMEOUT ago
        cache_time = time.time() - (CACHE_TIMEOUT.total_seconds() + 10)
        cached_value = (old_content, cache_time)

        mock_cache.get.return_value = cached_value

        with patch.object(
            fetcher,
            "_fetch_from_remote",
            side_effect=requests.RequestException("Timeout"),
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url)

            # Should return stale content instead of raising
            assert result == old_content
            mock_fetch.assert_called_once()

    def test_fetch_expired_cache(self, fetcher, mock_cache):
        """Test that expired cache (too old) forces refresh and raises on failure"""
        url = "http://example.com/cal.ics"
        old_content = "ANCIENT DATA"
        # Cache set longer than MAX_STALE_AGE ago
        cache_time = time.time() - (MAX_STALE_AGE.total_seconds() + 100)
        cached_value = (old_content, cache_time)

        mock_cache.get.return_value = cached_value

        # Scenario 1: Refresh succeeds
        with patch.object(
            fetcher,
            "_fetch_from_remote",
            return_value="NEW DATA",
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url)
            assert result == "NEW DATA"
            mock_fetch.assert_called_once()

        # Scenario 2: Refresh fails - should raise
        with (
            patch.object(
                fetcher,
                "_fetch_from_remote",
                side_effect=requests.RequestException("Timeout"),
            ),
            pytest.raises(requests.RequestException),
        ):
            fetcher.fetch_calendar(url)

    def test_legacy_cache_format(self, fetcher, mock_cache):
        """Test handling of legacy cache format (string instead of tuple)"""
        url = "http://example.com/cal.ics"
        content = "LEGACY DATA"

        # Legacy format: just the string, no timestamp
        mock_cache.get.return_value = content

        with patch.object(
            fetcher,
            "_fetch_from_remote",
            return_value="NEW DATA",
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url)

            # Should treat as stale and try to refresh
            assert result == "NEW DATA"
            mock_fetch.assert_called_once()

    def test_no_cache_hit(self, fetcher, mock_cache):
        """Test behavior when no cache exists"""
        url = "http://example.com/cal.ics"
        mock_cache.get.return_value = None

        with patch.object(
            fetcher,
            "_fetch_from_remote",
            return_value="FRESH DATA",
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url)

            assert result == "FRESH DATA"
            mock_fetch.assert_called_once()
            assert mock_cache.set.called

    def test_fetch_from_remote_success(self, fetcher, mock_requests):
        """Test underlying _fetch_from_remote logic"""
        url = "http://example.com/cal.ics"
        content = "CALENDAR CONTENT"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.content = content.encode("utf-8")
        # Fix: Mock text property to return content string so len() works
        mock_response.text = content
        mock_requests.return_value = mock_response

        result = fetcher._fetch_from_remote(url)  # noqa: SLF001
        assert result == content
        # Verify the actual default User-Agent used in implementation
        expected_headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }
        mock_requests.assert_called_with(url, headers=expected_headers, timeout=30)

    def test_fetch_from_remote_failure(self, fetcher, mock_requests):
        """Test underlying _fetch_from_remote logic on failure"""
        url = "http://example.com/cal.ics"
        mock_requests.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            fetcher._fetch_from_remote(url)  # noqa: SLF001
