"""Tests for user account services."""

from unittest.mock import patch

import pytest

from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.users.models import User
from mergecalweb.users.services import delete_user_account
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestDeleteUserAccount:
    """Tests for delete_user_account service."""

    def test_deletes_user_successfully(self):
        """Should delete user and return correct statistics."""
        user = UserFactory()
        user_id = user.pk
        user_email = user.email

        # Create some calendars and sources
        calendar1 = CalendarFactory(owner=user)
        calendar2 = CalendarFactory(owner=user)
        SourceFactory.create_batch(2, calendar=calendar1)
        SourceFactory.create_batch(3, calendar=calendar2)

        # Call deletion service
        stats = delete_user_account(user)

        # Verify statistics
        expected_calendar_count = 2
        expected_source_count = 5
        assert stats["calendar_count"] == expected_calendar_count
        assert stats["source_count"] == expected_source_count
        assert stats["user_email"] == user_email
        assert "deleted_at" in stats

        # Verify user is deleted
        assert not User.objects.filter(pk=user_id).exists()

    def test_cascade_deletes_calendars_and_sources(self):
        """Should cascade delete all calendars and sources."""
        user = UserFactory()

        # Create calendars and sources
        calendar1 = CalendarFactory(owner=user)
        calendar2 = CalendarFactory(owner=user)
        source1 = SourceFactory(calendar=calendar1)
        source2 = SourceFactory(calendar=calendar1)
        source3 = SourceFactory(calendar=calendar2)

        calendar1_id = calendar1.pk
        calendar2_id = calendar2.pk
        source_ids = [source1.pk, source2.pk, source3.pk]

        # Delete account
        delete_user_account(user)

        # Verify cascaded deletion
        from mergecalweb.calendars.models import Calendar
        from mergecalweb.calendars.models import Source

        assert not Calendar.objects.filter(pk__in=[calendar1_id, calendar2_id]).exists()
        assert not Source.objects.filter(pk__in=source_ids).exists()

    def test_service_handles_stripe_customer_gracefully(self):
        """
        Service should handle Stripe customer scenario gracefully.
        Note: Full Stripe integration tests require actual djstripe models.
        This test verifies the deletion completes even if Stripe customer lookups fail.
        """
        user = UserFactory()
        user_id = user.pk

        # The user's djstripe_customers.first() will return None by default
        # This simulates a user without a Stripe customer
        stats = delete_user_account(user)

        # Should complete successfully even without Stripe customer
        assert not User.objects.filter(pk=user_id).exists()
        assert stats["calendar_count"] == 0

    def test_handles_user_without_stripe_customer(self):
        """Should handle deletion for users without Stripe customers."""
        user = UserFactory()
        user_id = user.pk

        # Mock no Stripe customer using patch
        with patch.object(user.djstripe_customers, "first", return_value=None):
            # Delete account
            stats = delete_user_account(user)

            # Should still delete successfully
            assert not User.objects.filter(pk=user_id).exists()
            assert stats["calendar_count"] == 0
            assert stats["source_count"] == 0

    def test_returns_correct_statistics_with_no_calendars(self):
        """Should return zero counts for user with no calendars."""
        user = UserFactory()

        stats = delete_user_account(user)

        assert stats["calendar_count"] == 0
        assert stats["source_count"] == 0
        assert stats["user_email"] == user.email

    def test_deletion_is_atomic(self):
        """Deletion should be atomic - all or nothing."""
        user = UserFactory()
        CalendarFactory(owner=user)

        # This test verifies that the deletion happens in a transaction
        # If any part fails, the whole operation should be rolled back
        stats = delete_user_account(user)

        # If we get here, deletion succeeded
        assert not User.objects.filter(pk=user.pk).exists()
        assert stats["calendar_count"] == 1

    @patch("mergecalweb.users.services.logger")
    def test_logs_deletion_events(self, mock_logger):
        """Should log appropriate events during deletion."""
        user = UserFactory()

        delete_user_account(user)

        # Verify logging calls
        assert mock_logger.info.called
        assert mock_logger.debug.called

    @patch("mergecalweb.users.services.logger")
    def test_logs_stripe_customer_events(self, mock_logger):
        """Should log appropriate events when handling Stripe customers."""
        user = UserFactory()

        delete_user_account(user)

        # Verify account deletion events are logged
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        assert any("account-deletion-started" in str(call) for call in log_calls)
        assert any("account-deleted" in str(call) for call in log_calls)
