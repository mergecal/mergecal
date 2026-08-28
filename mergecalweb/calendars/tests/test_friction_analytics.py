"""Tests for the analytics events raised when validation turns a user away."""

from unittest.mock import patch

import pytest
from django.core.exceptions import ValidationError
from requests.exceptions import RequestException

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.calendars.models import validate_ical_url
from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.core.constants import CalendarLimits
from mergecalweb.core.constants import SourceLimits
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

FEED_URL = "https://calendar.example.com/private-token/basic.ics"


def only_call(mock) -> tuple[str, dict]:
    assert mock.call_count == 1, mock.call_args_list
    return mock.call_args[0][0], mock.call_args[1]


class TestSourceValidationFailed:
    @pytest.mark.parametrize(
        ("fetch_result", "expected_error_type"),
        [
            ("<!DOCTYPE html><html><body>Sign in</body></html>", "html-detected"),
            ("this is not a calendar", "parse"),
        ],
    )
    def test_a_feed_that_is_not_a_calendar_is_captured(
        self,
        fetch_result: str,
        expected_error_type: str,
    ):
        with (
            patch(
                "mergecalweb.calendars.models.CalendarFetcher.fetch_calendar",
                return_value=fetch_result,
            ),
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            validate_ical_url(FEED_URL)

        event, props = only_call(mock_capture)
        assert event == "source_validation_failed"
        assert props["error_type"] == expected_error_type

    def test_an_unreachable_feed_is_captured_by_host_alone(self):
        """Feed URLs carry access tokens in their path."""
        with (
            patch(
                "mergecalweb.calendars.models.CalendarFetcher.fetch_calendar",
                side_effect=RequestException("connection refused"),
            ),
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            validate_ical_url(FEED_URL)

        props = only_call(mock_capture)[1]
        assert props["error_type"] == "network"
        assert props["source_domain"] == "calendar.example.com"
        assert "private-token" not in str(props)

    def test_a_missing_mergecal_calendar_is_captured(self):
        missing = "https://example.com/calendars/8ad0f0f4-0000-0000-0000-000000000000/"
        with (
            patch("mergecalweb.calendars.models.is_local_url", return_value=True),
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            validate_ical_url(missing)

        assert only_call(mock_capture)[1]["error_type"] == "local-not-found"


class TestTierLimitHit:
    def test_a_free_user_at_the_calendar_limit_is_captured(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
        for _ in range(CalendarLimits.FREE):
            CalendarFactory(owner=user)

        with (
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            Calendar(name="One too many", owner=user, timezone="UTC").clean()

        event, props = only_call(mock_capture)
        assert event == "tier_limit_hit"
        assert props["limit_type"] == "calendar"
        assert props["user"] == user
        assert props["user_tier"] == User.SubscriptionTier.FREE
        assert props["current_count"] == CalendarLimits.FREE

    def test_a_calendar_at_the_source_limit_is_captured(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
        calendar = CalendarFactory(owner=user)
        for _ in range(SourceLimits.FREE):
            SourceFactory(calendar=calendar)

        with (
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            Source(name="One too many", url=FEED_URL, calendar=calendar).clean()

        event, props = only_call(mock_capture)
        assert event == "tier_limit_hit"
        assert props["limit_type"] == "source"
        assert props["calendar_uuid"] == str(calendar.uuid)


class TestTierFeatureDenied:
    @pytest.mark.parametrize(
        ("field", "value", "expected_feature"),
        [
            ("update_frequency_seconds", 3600, "custom-frequency"),
            ("remove_branding", True, "remove-branding"),
        ],
    )
    def test_a_free_user_reaching_a_calendar_gate_is_captured(
        self,
        field: str,
        value: object,
        expected_feature: str,
    ):
        user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
        calendar = Calendar(name="Gated", owner=user, timezone="UTC")
        setattr(calendar, field, value)

        with (
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            calendar.clean()

        event, props = only_call(mock_capture)
        assert event == "tier_feature_denied"
        assert props["feature"] == expected_feature
        assert props["user"] == user

    def test_a_personal_user_customizing_a_source_is_captured(self):
        # Personal rather than Free: a free user is stopped by the source
        # limit before the customization check is reached.
        user = UserFactory(subscription_tier=User.SubscriptionTier.PERSONAL)
        calendar = CalendarFactory(owner=user)

        with (
            patch("mergecalweb.calendars.models.capture") as mock_capture,
            pytest.raises(ValidationError),
        ):
            Source(
                name="Prefixed",
                url=FEED_URL,
                calendar=calendar,
                custom_prefix="[Work]",
            ).clean()

        event, props = only_call(mock_capture)
        assert event == "tier_feature_denied"
        assert props["feature"] == "source-customization"
