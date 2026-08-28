"""Tests for the analytics event raised when someone signs up."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from allauth.account.signals import user_signed_up

from mergecalweb.users.models import User

pytestmark = pytest.mark.django_db


def send_signup(user: User, **kwargs) -> None:
    user_signed_up.send(sender=User, request=None, user=user, **kwargs)


class TestUserSignedUp:
    @pytest.fixture(autouse=True)
    def _without_the_signup_emails(self):
        """The signal also sends mail and queues a task; not what's under test."""
        with (
            patch("mergecalweb.users.signals.send_welcome_email"),
            patch("mergecalweb.users.signals.schedule_follow_up_email"),
        ):
            yield

    def test_an_email_signup_is_captured(self, user: User):
        with patch("mergecalweb.users.signals.capture") as mock_capture:
            send_signup(user)

        event, props = mock_capture.call_args[0][0], mock_capture.call_args[1]
        assert event == "user_signed_up"
        assert props["signup_method"] == "email"
        # Named explicitly: the user isn't logged in yet, so there's no
        # request context to identify from.
        assert props["user"] == user

    def test_a_social_signup_records_its_provider(self, user: User):
        sociallogin = MagicMock()
        sociallogin.account.provider = "google"

        with patch("mergecalweb.users.signals.capture") as mock_capture:
            send_signup(user, sociallogin=sociallogin)

        assert mock_capture.call_args[1]["signup_method"] == "google"
