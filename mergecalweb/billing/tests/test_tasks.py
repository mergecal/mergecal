from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
import stripe
from djstripe.models import APIKey
from djstripe.models import Customer
from djstripe.models import Product
from djstripe.models import Subscription

from mergecalweb.billing.tasks import update_all_users_from_stripe_customers
from mergecalweb.billing.tasks import update_stripe_subscription
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

if TYPE_CHECKING:
    from collections.abc import Callable

pytestmark = pytest.mark.django_db


@pytest.fixture
def stored_subscription(
    stripe_api_key: APIKey,
    stripe_event: Callable[[str], dict],
) -> Callable[..., Subscription]:
    """Store a Stripe subscription for `user` on a product named after `tier`."""

    def store(user: User, tier: User.SubscriptionTier, event_type: str) -> Subscription:
        data = stripe_event(event_type)["data"]["object"]
        # Objects these tests don't need; dj-stripe would fetch each from the API.
        data["default_payment_method"] = None
        data["latest_invoice"] = None
        data["pending_setup_intent"] = None
        Customer.objects.create(id=data["customer"], subscriber=user)
        Product.objects.create(id=data["plan"]["product"], name=tier.label, active=True)
        return Subscription.sync_from_stripe_data(
            stripe.Subscription.construct_from(data, stripe_api_key.secret),
            api_key=stripe_api_key.secret,
        )

    return store


@pytest.mark.parametrize(
    "tier",
    [
        User.SubscriptionTier.PERSONAL,
        User.SubscriptionTier.BUSINESS,
        User.SubscriptionTier.SUPPORTER,
    ],
)
def test_update_stripe_subscription_sets_tier_from_trialing_subscription(
    stored_subscription: Callable[..., Subscription],
    user: User,
    tier: User.SubscriptionTier,
) -> None:
    stored_subscription(user, tier, "customer.subscription.created")

    update_stripe_subscription(user.id)

    user.refresh_from_db()
    assert user.subscription_tier == tier


def test_update_stripe_subscription_keeps_tier_when_only_subscription_is_canceled(
    stored_subscription: Callable[..., Subscription],
    user: User,
) -> None:
    stored_subscription(
        user,
        User.SubscriptionTier.BUSINESS,
        "customer.subscription.deleted",
    )
    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()

    update_stripe_subscription(user.id)

    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS


def test_update_stripe_subscription_without_customer_keeps_tier(user: User) -> None:
    user.subscription_tier = User.SubscriptionTier.PERSONAL
    user.save()

    update_stripe_subscription(user.id)

    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.PERSONAL


def test_update_all_users_syncs_each_customer_with_a_user(
    settings,
    stored_subscription: Callable[..., Subscription],
    user: User,
) -> None:
    settings.CELERY_TASK_ALWAYS_EAGER = True
    stored_subscription(
        user,
        User.SubscriptionTier.SUPPORTER,
        "customer.subscription.created",
    )
    Customer.objects.create(id="cus_without_user", subscriber=None)
    other_user = UserFactory()

    update_all_users_from_stripe_customers()

    user.refresh_from_db()
    other_user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.SUPPORTER
    assert other_user.subscription_tier == User.SubscriptionTier.FREE
