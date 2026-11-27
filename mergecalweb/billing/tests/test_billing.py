from __future__ import annotations

import hmac
import json
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.template.loader import render_to_string
from django.urls import reverse
from djstripe.enums import APIKeyType
from djstripe.models import Account
from djstripe.models import APIKey
from djstripe.models import Customer
from djstripe.models import Product
from djstripe.models import WebhookEndpoint

from mergecalweb.users.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    import responses
    from django.test import Client


@pytest.mark.django_db
def test_subscription_update_webhook_grants_business_tier(
    client: Client,
    http: responses.RequestsMock,
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event_type = "customer.subscription.updated"
    account = Account.objects.create(
        id="acct_mergecal_test",
        charges_enabled=True,
        details_submitted=True,
    )
    APIKey.objects.create(
        secret="sk_test_mergecalPlaceholderKey123",  # noqa: S106
        type=APIKeyType.secret,
        livemode=False,
        djstripe_owner_account=account,
    )
    endpoint = WebhookEndpoint.objects.create(
        id="we_mergecal_test",
        secret="whsec_mergecal_test",  # noqa: S106
        enabled_events=[event_type],
        djstripe_owner_account=account,
    )

    event = stripe_event(event_type)
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
    timestamp = int(time.time())

    payload = json.dumps(event)
    signature = hmac.digest(
        endpoint.secret.encode(),
        f"{timestamp}.{payload}".encode(),
        "sha256",
    ).hex()

    assert user.subscription_tier == User.SubscriptionTier.FREE
    response = client.post(
        reverse("djstripe:djstripe_webhook_by_uuid", args=[endpoint.djstripe_uuid]),
        data=payload,
        content_type="application/json",
        headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
    )

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
