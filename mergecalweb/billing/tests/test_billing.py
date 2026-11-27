from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING

import pytest
from django.template.loader import render_to_string
from djstripe.models import Customer
from djstripe.models import Event
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


@pytest.mark.django_db
def test_checkout_without_known_customer_is_acknowledged(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
) -> None:
    event = stripe_event("checkout.session.completed")
    session = event["data"]["object"]
    # Objects this test doesn't need; dj-stripe would fetch each from the API.
    session["payment_intent"] = None
    http.get(
        f"https://api.stripe.com/v1/checkout/sessions/{session['id']}",
        json=session,
    )

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    assert Event.objects.filter(id=event["id"]).exists()


@pytest.mark.parametrize(
    "event_type",
    ["customer.subscription.deleted", "customer.subscription.paused"],
)
@pytest.mark.django_db
def test_subscription_end_webhook_drops_user_to_free_tier(
    event_type: str,
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
    user: User,
) -> None:
    event = stripe_event(event_type)
    subscription = event["data"]["object"]
    # Objects this test doesn't need; dj-stripe would fetch each from the API.
    subscription["latest_invoice"] = None
    subscription["pending_setup_intent"] = None

    user.subscription_tier = User.SubscriptionTier.BUSINESS
    user.save()
    Customer.objects.create(id=subscription["customer"], subscriber=user)
    Product.objects.create(id=subscription["plan"]["product"], active=True)
    # dj-stripe re-fetches the subscription before running MergeCal's handler.
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription['id']}",
        json=subscription,
    )

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
    user.refresh_from_db()
    assert user.subscription_tier == User.SubscriptionTier.FREE


@pytest.mark.django_db
def test_subscription_end_webhook_without_user_is_acknowledged(
    http: responses.RequestsMock,
    send_stripe_webhook: Callable[[dict], HttpResponse],
    stripe_event: Callable[[str], dict],
) -> None:
    event = stripe_event("customer.subscription.deleted")
    subscription = event["data"]["object"]
    # Objects this test doesn't need; dj-stripe would fetch each from the API.
    subscription["latest_invoice"] = None

    Customer.objects.create(id=subscription["customer"])
    Product.objects.create(id=subscription["plan"]["product"], active=True)
    # dj-stripe re-fetches the subscription before running MergeCal's handler.
    http.get(
        f"https://api.stripe.com/v1/subscriptions/{subscription['id']}",
        json=subscription,
    )

    response = send_stripe_webhook(event)

    assert response.status_code == HTTPStatus.OK
