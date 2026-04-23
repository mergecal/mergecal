from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
from django.http import HttpRequest

from mergecalweb.billing.signals import create_stripe_customer
from mergecalweb.users.tests.factories import UserFactory


@pytest.mark.django_db
class TestCreateStripeCustomer:
    """Test the create_stripe_customer signal handler."""

    def test_orphaned_customer_metadata_updated(self):
        """Test that orphaned customer metadata is updated with user ID."""
        # Create a user
        user = UserFactory()
        request = HttpRequest()

        # Create a mock orphaned customer (no subscriber)
        mock_customer = MagicMock()
        mock_customer.id = "cus_test123"
        mock_customer.email = user.email
        mock_customer.subscriber = None

        with (
            patch("mergecalweb.billing.signals.Customer.objects.filter") as mock_filter,
            patch("mergecalweb.billing.signals.stripe.Customer.modify") as mock_modify,
        ):
            # Set up the mock to return the orphaned customer
            mock_filter.return_value = [mock_customer]

            # Trigger the signal
            create_stripe_customer(
                sender=None,
                request=request,
                user=user,
            )

            # Verify that the customer was attached to the user
            assert mock_customer.subscriber == user
            mock_customer.save.assert_called_once()

            # Verify that Stripe customer metadata was updated
            mock_modify.assert_called_once_with(
                mock_customer.id,
                metadata={"djstripe_subscriber": str(user.pk)},
            )

    def test_no_orphaned_customers(self):
        """Test creating a new customer when none exist."""
        user = UserFactory()
        request = HttpRequest()

        mock_customer = MagicMock()
        mock_customer.id = "cus_test456"

        with (
            patch("mergecalweb.billing.signals.Customer.objects.filter") as mock_filter,
            patch(
                "mergecalweb.billing.signals.Customer.get_or_create",
            ) as mock_get_or_create,
            patch("mergecalweb.billing.signals.Price.objects.get") as mock_price_get,
            patch("mergecalweb.billing.signals.stripe.Subscription.create") as mock_sub,
            patch("mergecalweb.billing.signals.stripe.Customer.modify") as mock_modify,
        ):
            # Set up mocks
            mock_filter.return_value = []  # No existing customers
            mock_get_or_create.return_value = (mock_customer, True)  # New customer
            mock_price = MagicMock(id="price_123", lookup_key="business_monthly")
            mock_price_get.return_value = mock_price

            # Trigger the signal
            create_stripe_customer(
                sender=None,
                request=request,
                user=user,
            )

            # Verify subscription was created for new customer
            mock_sub.assert_called_once()

            # Verify that metadata update was NOT called for new customers
            mock_modify.assert_not_called()

    def test_customer_already_has_subscriber(self):
        """Test that customers with subscribers are not modified."""
        user = UserFactory()
        request = HttpRequest()

        # Create a mock customer that already has a subscriber
        mock_customer = MagicMock()
        mock_customer.id = "cus_test789"
        mock_customer.email = user.email
        mock_customer.subscriber = user  # Already has subscriber

        with (
            patch("mergecalweb.billing.signals.Customer.objects.filter") as mock_filter,
            patch("mergecalweb.billing.signals.stripe.Customer.modify") as mock_modify,
        ):
            # Set up the mock to return the customer with subscriber
            mock_filter.return_value = [mock_customer]

            # Trigger the signal
            create_stripe_customer(
                sender=None,
                request=request,
                user=user,
            )

            # Verify that the customer was NOT saved (no changes)
            mock_customer.save.assert_not_called()

            # Verify that metadata update was NOT called
            mock_modify.assert_not_called()

