"""Tests for the analytics events raised by calendar and source lifecycle."""

from unittest.mock import patch

import pytest

from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def captured(mock, event: str) -> dict:
    """Properties of the one call that captured `event`."""
    calls = [c for c in mock.call_args_list if c[0][0] == event]
    assert len(calls) == 1, f"expected one {event}, got {len(calls)}"
    return calls[0][1]


class TestCalendarCreated:
    def test_a_new_calendar_is_captured_against_its_owner(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.BUSINESS)
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            calendar = CalendarFactory(owner=user)

        props = captured(mock_capture, "calendar_created")
        assert props["user"] == user
        assert props["calendar_uuid"] == str(calendar.uuid)
        assert props["user_tier"] == User.SubscriptionTier.BUSINESS

    @pytest.mark.parametrize(
        ("existing", "expected_first"),
        [(0, True), (1, False)],
    )
    def test_only_the_first_calendar_is_marked_as_first(
        self,
        existing: int,
        expected_first: bool,  # noqa: FBT001
    ):
        user = UserFactory()
        for _ in range(existing):
            CalendarFactory(owner=user)

        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            CalendarFactory(owner=user)

        props = captured(mock_capture, "calendar_created")
        assert props["is_first_calendar"] is expected_first
        assert props["calendar_count"] == existing + 1

    def test_the_count_reaches_the_person_profile(self):
        user = UserFactory()
        with patch("mergecalweb.calendars.signals.set_person_properties") as mock_set:
            CalendarFactory(owner=user)

        mock_set.assert_called_once_with(user, calendar_count=1)

    def test_editing_a_calendar_captures_nothing(self):
        calendar = CalendarFactory()
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            calendar.name = "Renamed"
            calendar.save()

        assert mock_capture.call_args_list == []


class TestSourceAdded:
    def test_a_new_source_is_captured_against_the_calendar_owner(self):
        calendar = CalendarFactory()
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            SourceFactory(calendar=calendar, url="https://example.com/feed.ics")

        props = captured(mock_capture, "source_added")
        assert props["user"] == calendar.owner
        assert props["calendar_uuid"] == str(calendar.uuid)
        assert props["source_count"] == 1

    def test_only_the_host_of_the_url_is_sent(self):
        """Feed URLs carry access tokens in their path."""
        calendar = CalendarFactory()
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            SourceFactory(
                calendar=calendar,
                url="https://calendar.google.com/ical/s3cret-token/basic.ics",
            )

        props = captured(mock_capture, "source_added")
        assert props["source_domain"] == "calendar.google.com"
        assert "s3cret-token" not in str(props)

    @pytest.mark.parametrize(
        ("url", "expected"),
        [
            ("https://www.meetup.com/some-group/events/ical/", "meetup"),
            ("https://example.com/feed.ics", "remote"),
        ],
    )
    def test_the_source_is_classified(self, url: str, expected: str):
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            SourceFactory(url=url)

        assert captured(mock_capture, "source_added")["source_type"] == expected

    def test_a_users_first_source_anywhere_is_marked_as_such(self):
        user = UserFactory()
        first_calendar = CalendarFactory(owner=user)
        second_calendar = CalendarFactory(owner=user)

        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            SourceFactory(calendar=first_calendar)
        assert captured(mock_capture, "source_added")["is_first_source"] is True

        # A different calendar, but not this user's first source.
        with patch("mergecalweb.calendars.signals.capture") as mock_capture:
            SourceFactory(calendar=second_calendar)
        assert captured(mock_capture, "source_added")["is_first_source"] is False
