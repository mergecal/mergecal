from __future__ import annotations

import hmac
import json
import time
from pathlib import Path
from typing import TYPE_CHECKING

import pytest
from django.urls import reverse
from djstripe.enums import APIKeyType
from djstripe.models import Account
from djstripe.models import APIKey
from djstripe.models import WebhookEndpoint

if TYPE_CHECKING:
    from collections.abc import Callable

    from django.http import HttpResponse
    from django.test import Client

STRIPE_EVENTS_DIR = Path(__file__).parent / "stripe_events"


@pytest.fixture
def stripe_event() -> Callable[[str], dict]:
    """Load a scrubbed Stripe sandbox event by type, e.g. "invoice.paid"."""

    def load(event_type: str) -> dict:
        return json.loads((STRIPE_EVENTS_DIR / f"{event_type}.json").read_text())

    return load


@pytest.fixture
def send_stripe_webhook(client: Client, db) -> Callable[[dict], HttpResponse]:
    """POST an event to the dj-stripe webhook endpoint with a valid signature."""
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
        enabled_events=["*"],
        djstripe_owner_account=account,
    )

    def send(event: dict) -> HttpResponse:
        timestamp = int(time.time())
        payload = json.dumps(event)
        signature = hmac.digest(
            endpoint.secret.encode(),
            f"{timestamp}.{payload}".encode(),
            "sha256",
        ).hex()
        return client.post(
            reverse("djstripe:djstripe_webhook_by_uuid", args=[endpoint.djstripe_uuid]),
            data=payload,
            content_type="application/json",
            headers={"Stripe-Signature": f"t={timestamp},v1={signature}"},
        )

    return send
