from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from djstripe.models import Customer
from djstripe.models import Product

from mergecalweb.users.models import User

if TYPE_CHECKING:
    from collections.abc import Callable

    import responses
    from django.http import HttpResponse


@pytest.mark.django_db
def test_paid_invoice_sets_tier_from_its_subscription(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event = stripe_event("invoice.paid")
    invoice = event["data"]["object"]
    subscription = stripe_event("customer.subscription.created")["data"]["object"]
    subscription["default_payment_method"] = None
    subscription["latest_invoice"] = None
    subscription["pending_setup_intent"] = None
    Customer.objects.create(id=invoice["customer"], subscriber=user)
    Product.objects.create(
        id=subscription["plan"]["product"],
        name=User.SubscriptionTier.BUSINESS.label,
        active=True,
    )
    http.get(f"https://api.stripe.com/v1/invoices/{invoice['id']}", json=invoice)
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription['id']}",
        json=subscription,
    )

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS


@pytest.mark.parametrize(
    "event_type",
    ["invoice.payment_failed", "invoice.payment_action_required"],
)
@pytest.mark.django_db
def test_unpaid_invoice_drops_user_to_free_tier(
    event_type: str,
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event = stripe_event(event_type)
    invoice = event["data"]["object"]
    invoice["payment_intent"] = None
    invoice["lines"]["data"] = []
    Customer.objects.create(id=invoice["customer"], subscriber=user)
    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()
    http.get(f"https://api.stripe.com/v1/invoices/{invoice['id']}", json=invoice)

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.FREE


@pytest.mark.parametrize("event_type", ["invoice.created", "invoice.finalized"])
@pytest.mark.django_db
def test_new_invoice_keeps_user_tier(
    event_type: str,
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event = stripe_event(event_type)
    invoice = event["data"]["object"]
    invoice["subscription"] = None
    invoice["lines"]["data"] = []
    Customer.objects.create(id=invoice["customer"], subscriber=user)
    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()
    http.get(f"https://api.stripe.com/v1/invoices/{invoice['id']}", json=invoice)

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.BUSINESS


@pytest.mark.parametrize(
    "event_type",
    [
        "invoice.created",
        "invoice.finalized",
        "invoice.payment_failed",
        "invoice.payment_action_required",
    ],
)
@pytest.mark.django_db
def test_invoice_for_customer_without_user_is_acknowledged(
    event_type: str,
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
) -> None:
    event = stripe_event(event_type)
    invoice = event["data"]["object"]
    invoice["subscription"] = None
    invoice["payment_intent"] = None
    invoice["lines"]["data"] = []
    Customer.objects.create(id=invoice["customer"], subscriber=None)
    http.get(f"https://api.stripe.com/v1/invoices/{invoice['id']}", json=invoice)

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
