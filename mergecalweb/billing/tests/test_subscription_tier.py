from __future__ import annotations

from datetime import timedelta
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.core import mail
from django.utils import timezone
from djstripe.models import Customer
from djstripe.models import Product

from mergecalweb.users.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    import responses
    from django.http import HttpResponse

SUBSCRIPTION_EVENTS = ["customer.subscription.created", "customer.subscription.updated"]


def prepare_subscription_event(
    http: responses.RequestsMock,
    event: dict,
    user: User,
    product_name: str,
) -> None:
    subscription = event["data"]["object"]
    # Objects these tests don't need; dj-stripe would fetch each from the API.
    subscription["default_payment_method"] = None
    subscription["latest_invoice"] = None
    subscription["pending_setup_intent"] = None
    Customer.objects.create(id=subscription["customer"], subscriber=user)
    Product.objects.create(
        id=subscription["plan"]["product"],
        name=product_name,
        active=True,
    )
    # dj-stripe re-fetches the subscription before running MergeCal's handler.
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription['id']}",
        json=subscription,
    )


@pytest.mark.django_db
@pytest.mark.parametrize("event_type", SUBSCRIPTION_EVENTS)
@pytest.mark.parametrize("status", ["active", "trialing"])
@pytest.mark.parametrize(
    "tier",
    [
        User.SubscriptionTier.PERSONAL,
        User.SubscriptionTier.BUSINESS,
        User.SubscriptionTier.SUPPORTER,
    ],
)
def test_subscription_webhook_maps_product_to_tier(  # noqa: PLR0913
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
    event_type: str,
    status: str,
    tier: User.SubscriptionTier,
) -> None:
    event = stripe_event(event_type)
    event["data"]["object"]["status"] = status
    prepare_subscription_event(http, event, user, tier.label)

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == tier


@pytest.mark.django_db
@pytest.mark.parametrize("event_type", SUBSCRIPTION_EVENTS)
@pytest.mark.parametrize(
    "status",
    ["past_due", "unpaid", "canceled", "incomplete", "incomplete_expired"],
)
def test_subscription_webhook_with_lapsed_status_drops_to_free(  # noqa: PLR0913
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
    event_type: str,
    status: str,
) -> None:
    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()
    event = stripe_event(event_type)
    event["data"]["object"]["status"] = status
    prepare_subscription_event(http, event, user, User.SubscriptionTier.BUSINESS.label)

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.FREE


@pytest.mark.django_db
def test_subscription_webhook_emails_existing_user_about_upgrade(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    user.date_joined = timezone.now() - timedelta(days=30)
    user.save()
    event = stripe_event("customer.subscription.updated")
    prepare_subscription_event(http, event, user, User.SubscriptionTier.PERSONAL.label)

    send_stripe_webhook(event)

    assert [m.to for m in mail.outbox] == [[user.email]]
    assert "Personal" in mail.outbox[0].subject


@pytest.mark.django_db
def test_subscription_webhook_skips_upgrade_email_for_new_user(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    user.date_joined = timezone.now() - timedelta(minutes=59)
    user.save()
    event = stripe_event("customer.subscription.created")
    prepare_subscription_event(http, event, user, User.SubscriptionTier.BUSINESS.label)

    send_stripe_webhook(event)

    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS
    assert mail.outbox == []


@pytest.mark.django_db
def test_subscription_webhook_without_tier_change_sends_no_email(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    user.date_joined = timezone.now() - timedelta(days=30)
    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()
    event = stripe_event("customer.subscription.updated")
    prepare_subscription_event(http, event, user, User.SubscriptionTier.BUSINESS.label)

    send_stripe_webhook(event)

    assert mail.outbox == []
