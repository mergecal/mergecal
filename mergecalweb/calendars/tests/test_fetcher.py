import re
from datetime import timedelta

import pytest
import requests
import time_machine
from django.core.cache import cache
from icalendar import Calendar
from responses import matchers

from mergecalweb.calendars.cache import source_data_cache_key
from mergecalweb.calendars.fetching.fetcher import CACHE_TIMEOUT
from mergecalweb.calendars.fetching.fetcher import MAX_STALE_AGE
from mergecalweb.calendars.fetching.fetcher import BrokenSourceUrlError
from mergecalweb.calendars.fetching.fetcher import CalendarFetcher
from mergecalweb.calendars.fetching.fetcher import SourceAccessDeniedError
from mergecalweb.calendars.fetching.fetcher import SourceTimeoutError
from mergecalweb.calendars.fetching.fetcher import SourceUnavailableError

URL = "http://example.com/cal.ics"


@pytest.fixture
def fetcher():
    return CalendarFetcher()


@pytest.fixture
def clock():
    with time_machine.travel("2030-01-01 12:00Z", tick=False) as traveller:
        yield traveller


class TestCalendarFetcher:
    def test_fresh_cache_skips_the_network(self, fetcher, http, clock):
        http.get(URL, body="FIRST")

        fetcher.fetch_calendar(URL)
        clock.shift(CACHE_TIMEOUT - timedelta(seconds=10))

        assert fetcher.fetch_calendar(URL) == "FIRST"
        assert len(http.calls) == 1

    def test_stale_cache_is_refreshed(self, fetcher, http, clock):
        http.get(URL, body="OLD")
        http.get(URL, body="NEW")

        fetcher.fetch_calendar(URL)
        clock.shift(CACHE_TIMEOUT + timedelta(seconds=10))

        assert fetcher.fetch_calendar(URL) == "NEW"
        assert fetcher.fetch_calendar(URL) == "NEW"
        assert len(http.calls) == 2  # noqa: PLR2004

    def test_stale_cache_is_served_when_refresh_fails(self, fetcher, http, clock):
        http.get(URL, body="OLD")
        http.get(URL, body=requests.ConnectionError("down"))

        fetcher.fetch_calendar(URL)
        clock.shift(CACHE_TIMEOUT + timedelta(seconds=10))

        assert fetcher.fetch_calendar(URL) == "OLD"
        assert len(http.calls) == 2  # noqa: PLR2004

    @pytest.mark.parametrize("status", [404, 421, 423])
    def test_stale_cache_is_served_after_http_error(self, fetcher, http, clock, status):
        http.get(URL, body="OLD")
        http.get(URL, status=status)

        fetcher.fetch_calendar(URL)
        clock.shift(CACHE_TIMEOUT + timedelta(seconds=10))

        assert fetcher.fetch_calendar(URL) == "OLD"

    def test_expired_cache_is_refetched(self, fetcher, http, clock):
        http.get(URL, body="OLD")
        http.get(URL, body="NEW")

        fetcher.fetch_calendar(URL)
        cache.touch(source_data_cache_key(URL), timeout=None)
        clock.shift(MAX_STALE_AGE + timedelta(seconds=100))

        assert fetcher.fetch_calendar(URL) == "NEW"

    def test_expired_cache_raises_when_refetch_fails(self, fetcher, http, clock):
        http.get(URL, body="OLD")
        http.get(URL, body=requests.ConnectionError("down"))

        fetcher.fetch_calendar(URL)
        cache.touch(source_data_cache_key(URL), timeout=None)
        clock.shift(MAX_STALE_AGE + timedelta(seconds=100))

        with pytest.raises(SourceUnavailableError):
            fetcher.fetch_calendar(URL)

    def test_legacy_cache_format_is_refreshed(self, fetcher, http):
        cache.set(source_data_cache_key(URL), "LEGACY DATA")
        http.get(URL, body="NEW DATA")

        assert fetcher.fetch_calendar(URL) == "NEW DATA"

    def test_cache_miss_fetches_and_caches(self, fetcher, http):
        http.get(URL, body="FRESH DATA")

        assert fetcher.fetch_calendar(URL) == "FRESH DATA"
        content, _cached_at = cache.get(source_data_cache_key(URL))
        assert content == "FRESH DATA"

    def test_request_headers_and_timeout(self, fetcher, http):
        http.get(
            URL,
            body="CALENDAR CONTENT",
            match=[
                matchers.header_matcher(
                    {
                        "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
                        "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
                        "Accept-Language": "en-US,en;q=0.9",
                    },
                ),
                matchers.request_kwargs_matcher({"timeout": 30}),
            ],
        )

        assert fetcher.fetch_calendar(URL) == "CALENDAR CONTENT"

    def test_connection_error_is_unavailable_without_status(self, fetcher, http):
        http.get(URL, body=requests.ConnectionError("Network error"))

        with pytest.raises(SourceUnavailableError) as excinfo:
            fetcher.fetch_calendar(URL)

        assert excinfo.value.status_code is None

    def test_timeout_raises_timeout(self, fetcher, http):
        http.get(URL, body=requests.ReadTimeout("slow"))

        with pytest.raises(SourceTimeoutError):
            fetcher.fetch_calendar(URL)

    @pytest.mark.parametrize("status", [400, 404, 410])
    def test_rejected_url_is_broken(self, fetcher, http, status):
        http.get(URL, status=status)

        with pytest.raises(BrokenSourceUrlError) as excinfo:
            fetcher.fetch_calendar(URL)

        assert excinfo.value.status_code == status

    @pytest.mark.parametrize("status", [401, 403])
    def test_refused_access_is_denied(self, fetcher, http, status):
        http.get(URL, status=status)

        with pytest.raises(SourceAccessDeniedError) as excinfo:
            fetcher.fetch_calendar(URL)

        assert excinfo.value.status_code == status

    @pytest.mark.parametrize(
        "url",
        ["ftp://example.com/cal.ics", "example.com/cal.ics", "http://"],
    )
    def test_malformed_url_is_broken(self, fetcher, http, url):
        with pytest.raises(BrokenSourceUrlError) as excinfo:
            fetcher.fetch_calendar(url)

        assert excinfo.value.status_code is None

    def test_redirect_loop_is_broken(self, fetcher, http):
        http.get(URL, status=302, headers={"Location": URL})

        with pytest.raises(BrokenSourceUrlError):
            fetcher.fetch_calendar(URL)

    @pytest.mark.parametrize("status", [408, 421, 423, 425, 429, 500, 502, 503])
    def test_server_side_failure_is_unavailable(self, fetcher, http, status):
        http.get(URL, status=status)

        with pytest.raises(SourceUnavailableError) as excinfo:
            fetcher.fetch_calendar(URL)

        assert excinfo.value.status_code == status


class TestCalendarFetcherLineEndings:
    def test_lone_cr_feed_parses_after_fetch(self, fetcher, http, test_calendars_dir):
        """TeamSnap ONE mixes LF, CRLF and a lone CR before END:VCALENDAR."""
        feed = (test_calendars_dir / "teamsnap_one.ics").read_bytes()
        http.get(URL, body=feed)

        result = fetcher.fetch_calendar(URL)

        calendar = Calendar.from_ical(result.encode())
        events = calendar.walk("VEVENT")
        assert [event["UID"] for event in events] == [
            "event-1@example.com",
            "event-2@example.com",
            "event-3@example.com",
        ]
        assert [event.decoded("DURATION") for event in events] == [
            timedelta(hours=1, minutes=30),
            timedelta(hours=1),
            timedelta(hours=1, minutes=30),
        ]

    def test_line_endings_are_normalized_to_crlf(
        self,
        fetcher,
        http,
        test_calendars_dir,
    ):
        """Mixed terminators are rewritten so content lines are RFC 5545 folded."""
        feed = (test_calendars_dir / "teamsnap_one.ics").read_bytes()
        http.get(URL, body=feed)

        result = fetcher.fetch_calendar(URL)

        stripped = result.replace("\r\n", "")
        assert "\r" not in stripped
        assert "\n" not in stripped
        assert result.count("\r\n") == len(re.findall(rb"\r\n|\r|\n", feed))

    def test_crlf_feed_is_unchanged(self, fetcher, http, test_calendars_dir):
        """A standard RFC 5545 feed keeps its bytes and its folded lines parse."""
        feed = (test_calendars_dir / "crlf.ics").read_bytes()
        http.get(URL, body=feed)

        result = fetcher.fetch_calendar(URL)

        assert result.encode() == feed
        [event] = Calendar.from_ical(result.encode()).walk("VEVENT")
        assert event["DESCRIPTION"] == (
            "A description long enough that the server folds it onto a second "
            "content line"
        )
