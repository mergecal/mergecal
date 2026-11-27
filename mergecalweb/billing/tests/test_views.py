from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from urllib.parse import parse_qs

import pytest
from django.urls import reverse
from djstripe.models import Customer

if TYPE_CHECKING:
    import responses
    from django.test import Client

    from mergecalweb.users.models import User


@pytest.mark.django_db
def test_pricing_page_for_anonymous_user_prompts_sign_in(client: Client) -> None:
    response = client.get(reverse("pricing"))

    assert response.status_code == HTTPStatus.OK
    assert "customer-session-client-secret" not in response.content.decode()
    assert reverse("account_login") in response.content.decode()


@pytest.mark.django_db
def test_pricing_page_for_signed_in_user_passes_customer_session(
    client: Client,
    http: responses.RequestsMock,
    user: User,
) -> None:
    customer = Customer.objects.create(id="cus_pricing_test", subscriber=user)
    client.force_login(user)
    sessions = http.post(
        "https://api.stripe.com/v1/customer_sessions",
        json={"object": "customer_session", "client_secret": "cuss_secret_test"},
    )

    response = client.get(reverse("pricing"))

    assert response.status_code == HTTPStatus.OK
    assert (
        'customer-session-client-secret="cuss_secret_test"' in response.content.decode()
    )
    assert parse_qs(sessions.calls[0].request.body)["customer"] == [customer.id]


@pytest.mark.django_db
def test_manage_billing_redirects_to_stripe_portal(
    client: Client,
    http: responses.RequestsMock,
    user: User,
) -> None:
    customer = Customer.objects.create(id="cus_portal_test", subscriber=user)
    client.force_login(user)
    portal_url = "https://billing.stripe.com/p/session/test_portal"
    sessions = http.post(
        "https://api.stripe.com/v1/billing_portal/sessions",
        json={"object": "billing_portal.session", "url": portal_url},
    )

    response = client.post(reverse("billing:manage_billing"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url == portal_url
    sent = parse_qs(sessions.calls[0].request.body)
    assert sent["customer"] == [customer.id]
    assert sent["return_url"] == [
        "http://testserver"
        + reverse("users:detail", kwargs={"username": user.username}),
    ]


@pytest.mark.django_db
def test_manage_billing_sends_anonymous_user_to_login(client: Client) -> None:
    response = client.post(reverse("billing:manage_billing"))

    assert response.status_code == HTTPStatus.FOUND
    assert response.url.startswith(reverse("account_login"))
