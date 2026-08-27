"""Tests for the PostHog analytics wrapper."""

from unittest.mock import patch

import pytest

from mergecalweb.core.analytics import AnalyticsEvent
from mergecalweb.core.analytics import capture
from mergecalweb.core.analytics import set_person_properties
from mergecalweb.core.analytics import source_domain
from mergecalweb.users.models import User


class TestSourceDomain:
    def test_keeps_only_the_host(self):
        url = "https://calendar.google.com/calendar/ical/abc123secret/basic.ics"
        assert source_domain(url) == "calendar.google.com"

    def test_returns_none_for_a_hostless_url(self):
        assert source_domain("not-a-url") is None


class TestCaptureWithoutAKey:
    """A blank POSTHOG_API_KEY is the local and test default."""

    def test_capture_does_nothing(self, settings):
        settings.POSTHOG_API_KEY = ""
        with patch("mergecalweb.core.analytics.posthog.capture") as mock_capture:
            capture(AnalyticsEvent.PRICING_VIEWED)
        mock_capture.assert_not_called()

    @pytest.mark.django_db
    def test_person_update_does_nothing(self, settings, user: User):
        settings.POSTHOG_API_KEY = ""
        with patch("mergecalweb.core.analytics.posthog.set") as mock_set:
            set_person_properties(user, subscription_tier=user.subscription_tier)
        mock_set.assert_not_called()


class TestCapture:
    @pytest.fixture(autouse=True)
    def _enable_posthog(self, settings):
        settings.POSTHOG_API_KEY = "phc_test"

    def test_sends_the_event_with_its_properties(self):
        with patch("mergecalweb.core.analytics.posthog.capture") as mock_capture:
            capture(AnalyticsEvent.TIER_LIMIT_HIT, limit_type="calendar")

        event, kwargs = mock_capture.call_args[0][0], mock_capture.call_args[1]
        assert event == "tier_limit_hit"
        assert kwargs["properties"] == {"limit_type": "calendar"}

    def test_omits_distinct_id_so_the_request_context_supplies_it(self):
        with patch("mergecalweb.core.analytics.posthog.capture") as mock_capture:
            capture(AnalyticsEvent.SOURCE_VALIDATION_FAILED, error_type="network")

        assert "distinct_id" not in mock_capture.call_args[1]

    @pytest.mark.django_db
    def test_identifies_a_user_by_their_django_pk(self, user: User):
        """Must match posthog.identify in base.html and the Stripe person key."""
        with patch("mergecalweb.core.analytics.posthog.capture") as mock_capture:
            capture(AnalyticsEvent.USER_SIGNED_UP, user=user)

        assert mock_capture.call_args[1]["distinct_id"] == str(user.pk)

    def test_drops_properties_with_no_value(self):
        with patch("mergecalweb.core.analytics.posthog.capture") as mock_capture:
            capture(
                AnalyticsEvent.SOURCE_ADDED,
                source_domain=None,
                calendar_uuid="abc",
            )

        assert mock_capture.call_args[1]["properties"] == {"calendar_uuid": "abc"}

    def test_a_posthog_failure_never_reaches_the_caller(self):
        with patch(
            "mergecalweb.core.analytics.posthog.capture",
            side_effect=RuntimeError("posthog is down"),
        ):
            capture(AnalyticsEvent.CALENDAR_CREATED)

    @pytest.mark.django_db
    def test_person_properties_are_set_on_the_user(self, user: User):
        with patch("mergecalweb.core.analytics.posthog.set") as mock_set:
            set_person_properties(user, calendar_count=3, subscription_tier=None)

        assert mock_set.call_args[1]["distinct_id"] == str(user.pk)
        assert mock_set.call_args[1]["properties"] == {"calendar_count": 3}

    @pytest.mark.django_db
    def test_a_posthog_failure_on_person_update_never_reaches_the_caller(
        self,
        user: User,
    ):
        with patch(
            "mergecalweb.core.analytics.posthog.set",
            side_effect=RuntimeError("posthog is down"),
        ):
            set_person_properties(user, calendar_count=1)
