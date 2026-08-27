"""Tests for the analytics events raised along the upgrade path."""

from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from mergecalweb.billing.signals import handle_checkout_session_completed
from mergecalweb.billing.signals import handle_subscription_end
from mergecalweb.billing.signals import update_user_subscription_tier
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


def stripe_subscription(status: str, product_name: str) -> MagicMock:
    subscription = MagicMock()
    subscription.status = status
    subscription.plan.product.name = product_name
    return subscription


def stripe_event(customer_id: str = "cus_123", event_type: str = "") -> MagicMock:
    event = MagicMock()
    event.data = {"object": {"customer": customer_id}}
    event.type = event_type
    return event


def customer_for(user: User | None) -> MagicMock:
    customer = MagicMock()
    customer.subscriber = user
    return customer


class TestSubscriptionTierChanged:
    def test_an_upgrade_is_captured_with_both_tiers(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
        subscription = stripe_subscription("active", "Business Tier")

        with (
            patch("mergecalweb.billing.signals.capture") as mock_capture,
            patch("mergecalweb.billing.signals.upgrade_subscription_email"),
        ):
            update_user_subscription_tier(user, subscription)

        event, props = mock_capture.call_args[0][0], mock_capture.call_args[1]
        assert event == "subscription_tier_changed"
        assert props["user"] == user
        assert props["old_tier"] == User.SubscriptionTier.FREE
        assert props["new_tier"] == User.SubscriptionTier.BUSINESS
        assert props["subscription_status"] == "active"
        assert props["plan_name"] == "Business Tier"

    def test_the_new_tier_reaches_the_person_profile(self):
        """Feature flags and surveys read stored properties, not events."""
        user = UserFactory(subscription_tier=User.SubscriptionTier.FREE)
        subscription = stripe_subscription("trialing", "Supporter Tier")

        with (
            patch("mergecalweb.billing.signals.set_person_properties") as mock_set,
            patch("mergecalweb.billing.signals.upgrade_subscription_email"),
        ):
            update_user_subscription_tier(user, subscription)

        mock_set.assert_called_once_with(
            user,
            subscription_tier=User.SubscriptionTier.SUPPORTER,
        )

    def test_a_webhook_that_changes_nothing_captures_nothing(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.BUSINESS)
        subscription = stripe_subscription("active", "Business Tier")

        with patch("mergecalweb.billing.signals.capture") as mock_capture:
            update_user_subscription_tier(user, subscription)

        assert mock_capture.call_args_list == []


class TestCheckoutCompleted:
    def test_a_completed_checkout_is_captured(self):
        user = UserFactory()

        with (
            patch(
                "mergecalweb.billing.signals.Customer.objects.get",
                return_value=customer_for(user),
            ),
            patch("mergecalweb.billing.signals.capture") as mock_capture,
        ):
            handle_checkout_session_completed(sender=None, event=stripe_event())

        event, props = mock_capture.call_args[0][0], mock_capture.call_args[1]
        assert event == "checkout_completed"
        assert props["user"] == user

    def test_a_customer_with_no_user_captures_nothing(self):
        with (
            patch(
                "mergecalweb.billing.signals.Customer.objects.get",
                return_value=customer_for(None),
            ),
            patch("mergecalweb.billing.signals.capture") as mock_capture,
        ):
            handle_checkout_session_completed(sender=None, event=stripe_event())

        assert mock_capture.call_args_list == []


class TestSubscriptionEnded:
    def test_the_end_of_a_subscription_is_captured(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.SUPPORTER)

        with (
            patch(
                "mergecalweb.billing.signals.Customer.objects.get",
                return_value=customer_for(user),
            ),
            patch("mergecalweb.billing.signals.capture") as mock_capture,
        ):
            handle_subscription_end(
                sender=None,
                event=stripe_event(event_type="customer.subscription.deleted"),
            )

        event, props = mock_capture.call_args[0][0], mock_capture.call_args[1]
        assert event == "subscription_ended"
        assert props["user"] == user
        assert props["old_tier"] == User.SubscriptionTier.SUPPORTER
        assert props["webhook_type"] == "customer.subscription.deleted"

    def test_the_downgrade_reaches_the_person_profile(self):
        user = UserFactory(subscription_tier=User.SubscriptionTier.BUSINESS)

        with (
            patch(
                "mergecalweb.billing.signals.Customer.objects.get",
                return_value=customer_for(user),
            ),
            patch("mergecalweb.billing.signals.set_person_properties") as mock_set,
        ):
            handle_subscription_end(sender=None, event=stripe_event())

        mock_set.assert_called_once_with(
            user,
            subscription_tier=User.SubscriptionTier.FREE,
        )
