import time
from unittest.mock import Mock
from unittest.mock import patch

import pytest
import requests

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
    def test_cache_hit_returns_immediately(self, fetcher, mock_cache):
        """Any valid cache hit returns immediately without a network request"""
        url = "http://example.com/cal.ics"
        content = "CALENDAR DATA"
        # Even "old" content is returned immediately — cache TTL enforces max age
        mock_cache.get.return_value = (content, time.time() - 1000)

        with patch.object(fetcher, "_fetch_from_remote") as mock_fetch:
            result = fetcher.fetch_calendar(url)

        assert result == content
        mock_fetch.assert_not_called()

    def test_cache_miss_fetches_from_remote(self, fetcher, mock_cache):
        """On cache miss, fetches from remote and caches the result"""
        url = "http://example.com/cal.ics"
        mock_cache.get.return_value = None

        with patch.object(
            fetcher, "_fetch_from_remote", return_value="FRESH DATA",
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url)

        assert result == "FRESH DATA"
        mock_fetch.assert_called_once_with(url, None)
        assert mock_cache.set.called

    def test_force_refresh_bypasses_cache(self, fetcher, mock_cache):
        """force_refresh=True fetches from remote even when cache is populated"""
        url = "http://example.com/cal.ics"
        mock_cache.get.return_value = ("CACHED DATA", time.time())

        with patch.object(
            fetcher, "_fetch_from_remote", return_value="FRESH DATA",
        ) as mock_fetch:
            result = fetcher.fetch_calendar(url, force_refresh=True)

        assert result == "FRESH DATA"
        mock_fetch.assert_called_once_with(url, None)
        mock_cache.get.assert_not_called()

    def test_force_refresh_updates_cache(self, fetcher, mock_cache):
        """force_refresh=True stores fresh content in cache"""
        url = "http://example.com/cal.ics"

        with patch.object(fetcher, "_fetch_from_remote", return_value="FRESH DATA"):
            fetcher.fetch_calendar(url, force_refresh=True)

        assert mock_cache.set.called

    def test_cache_miss_raises_on_remote_failure(self, fetcher, mock_cache):
        """On cache miss, a remote failure propagates as an exception"""
        url = "http://example.com/cal.ics"
        mock_cache.get.return_value = None

        with (
            patch.object(
                fetcher,
                "_fetch_from_remote",
                side_effect=requests.RequestException("Timeout"),
            ),
            pytest.raises(requests.RequestException),
        ):
            fetcher.fetch_calendar(url)

    def test_fetch_from_remote_success(self, fetcher, mock_requests):
        """_fetch_from_remote returns content and sends correct headers"""
        url = "http://example.com/cal.ics"
        content = "CALENDAR CONTENT"

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = content
        mock_requests.return_value = mock_response

        result = fetcher._fetch_from_remote(url)  # noqa: SLF001
        assert result == content
        expected_headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
        }
        mock_requests.assert_called_with(url, headers=expected_headers, timeout=30)

    def test_fetch_from_remote_failure(self, fetcher, mock_requests):
        """_fetch_from_remote raises on network error"""
        url = "http://example.com/cal.ics"
        mock_requests.side_effect = requests.RequestException("Network error")

        with pytest.raises(requests.RequestException):
            fetcher._fetch_from_remote(url)  # noqa: SLF001
