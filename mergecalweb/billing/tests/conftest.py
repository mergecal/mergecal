from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from collections.abc import Callable

STRIPE_EVENTS_DIR = Path(__file__).parent / "stripe_events"


@pytest.fixture
def stripe_event() -> Callable[[str], dict]:
    """Load a scrubbed Stripe sandbox event by type, e.g. "invoice.paid"."""

    def load(event_type: str) -> dict:
        return json.loads((STRIPE_EVENTS_DIR / f"{event_type}.json").read_text())

    return load
