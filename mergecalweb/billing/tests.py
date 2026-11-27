from __future__ import annotations

import hmac
import json
import time
from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse
from djstripe.enums import APIKeyType
from djstripe.models import Account
from djstripe.models import APIKey
from djstripe.models import Customer
from djstripe.models import Plan
from djstripe.models import Product
from djstripe.models import WebhookEndpoint

from mergecalweb.users.models import User

if TYPE_CHECKING:
    import responses
    from django.test import Client


@pytest.mark.django_db
def test_subscription_update_webhook_grants_business_tier(
    client: Client,
    http: responses.RequestsMock,
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

    customer = Customer.objects.create(id="cus_mergecal_test", subscriber=user)
    product = Product.objects.create(
        id="prod_mergecal_test",
        name=User.SubscriptionTier.BUSINESS.label,
        active=True,
    )
    plan = Plan.objects.create(
        id="plan_mergecal_test",
        product=product,
        active=True,
        currency="usd",
        interval="month",
    )

    timestamp = int(time.time())
    subscription_id = "sub_mergecal_test"
    subscription_item = {
        "id": "si_mergecal_test",
        "object": "subscription_item",
        "plan": plan.id,
        "subscription": subscription_id,
    }
    subscription = {
        "id": subscription_id,
        "object": "subscription",
        "livemode": False,
        "customer": customer.id,
        "plan": plan.id,
        "status": "active",
        "collection_method": "charge_automatically",
        "cancel_at_period_end": False,
        "current_period_start": timestamp,
        "current_period_end": timestamp + 3600,
        "items": {"object": "list", "data": [subscription_item], "has_more": False},
    }
    # dj-stripe re-fetches the subscription before running MergeCal's handler.
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription_id}",
        json=subscription,
    )

    event = {
        "id": "evt_mergecal_test",
        "object": "event",
        "type": event_type,
        "livemode": False,
        "created": timestamp,
        "data": {"object": subscription},
    }
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
