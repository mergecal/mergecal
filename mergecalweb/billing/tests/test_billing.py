from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.template.loader import render_to_string
from djstripe.models import Customer
from djstripe.models import Product

from mergecalweb.users.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    import responses
    from django.http import HttpResponse
    from django.test import Client


@pytest.mark.django_db
def test_subscription_update_webhook_grants_business_tier(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event = stripe_event("customer.subscription.updated")
    subscription = event["data"]["object"]
    # Objects this test doesn't need; dj-stripe would fetch each from the API.
    subscription["default_payment_method"] = None
    subscription["latest_invoice"] = None
    subscription["pending_setup_intent"] = None

    Customer.objects.create(id=subscription["customer"], subscriber=user)
    Product.objects.create(
        id=subscription["plan"]["product"],
        name=User.SubscriptionTier.BUSINESS.label,
        active=True,
    )
    # dj-stripe re-fetches the subscription before running MergeCal's handler.
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription['id']}",
        json=subscription,
    )
    assert user.subscription_tier == User.SubscriptionTier.FREE

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS


@pytest.mark.parametrize(
    ("days_left", "expected"),
    [(1, "1 day left."), (13, "13 days left.")],
)
def test_trial_banner_pluralizes_days_left(days_left: int, expected: str) -> None:
    html = render_to_string(
        "trialing.html",
        {"is_trial": True, "trial_days_left": days_left},
    )

    assert expected in html


@pytest.mark.django_db
def test_first_login_starts_business_trial_tier_immediately(
    client: Client,
    user: User,
) -> None:
    assert user.subscription_tier == User.SubscriptionTier.FREE

    client.force_login(user)

    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS
