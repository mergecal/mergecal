"""Tests for timezone utility functions."""

from __future__ import annotations

from mergecalweb.calendars.timezone_utils import normalize_timezone_name


def test_normalize_windows_timezone_to_iana() -> None:
    """Test that Windows timezone names are converted to IANA identifiers."""
    assert normalize_timezone_name("Eastern Standard Time") == "America/New_York"
    assert normalize_timezone_name("Central Standard Time") == "America/Chicago"
    assert normalize_timezone_name("Pacific Standard Time") == "America/Los_Angeles"
    assert normalize_timezone_name("GMT Standard Time") == "Europe/London"


def test_normalize_already_iana_timezone() -> None:
    """Test that IANA timezone identifiers are returned unchanged."""
    assert normalize_timezone_name("America/New_York") == "America/New_York"
    assert normalize_timezone_name("Europe/London") == "Europe/London"
    assert normalize_timezone_name("Asia/Tokyo") == "Asia/Tokyo"


def test_normalize_unknown_timezone() -> None:
    """Test that unknown timezone names are returned unchanged."""
    assert normalize_timezone_name("Unknown/Timezone") == "Unknown/Timezone"
    assert normalize_timezone_name("Custom Timezone") == "Custom Timezone"


def test_normalize_common_windows_timezones() -> None:
    """Test common Windows timezone conversions."""
    test_cases = {
        "Eastern Standard Time": "America/New_York",
        "Mountain Standard Time": "America/Denver",
        "Alaskan Standard Time": "America/Anchorage",
        "Hawaiian Standard Time": "Pacific/Honolulu",
        "India Standard Time": "Asia/Kolkata",
        "China Standard Time": "Asia/Shanghai",
        "Tokyo Standard Time": "Asia/Tokyo",
        "AUS Eastern Standard Time": "Australia/Sydney",
        "W. Europe Standard Time": "Europe/Berlin",
        "Central Europe Standard Time": "Europe/Budapest",
    }

    for windows_tz, iana_tz in test_cases.items():
        assert normalize_timezone_name(windows_tz) == iana_tz
