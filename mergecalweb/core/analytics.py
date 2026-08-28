"""
Product analytics events for PostHog.

These are the journey moments — signup, setup, friction, upgrade — that funnels
and cohorts are built from. They are separate from structured logging (see
`logging_events.py`): logs explain a request, events explain a user.

A person is identified by their Django user pk, matching `posthog.identify` in
`base.html` and the Stripe warehouse properties keyed on the same value.
Anything else silently creates a second person. Inside a request
`PosthogContextMiddleware` supplies it, so only webhooks and background tasks
need to pass `user=`.

Two conventions apply at every call site:
    - Never send `email`. The middleware already tags the request context
      with it.
    - Never send a full source URL. Send `source_domain(url)`: some calendar
      feeds carry an access token in their path.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING
from typing import Any
from urllib.parse import urlparse

import posthog
from django.conf import settings

if TYPE_CHECKING:
    from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


class AnalyticsEvent:
    """PostHog event names, in `object_verb` form.

    The browser sends three more of its own — feed_url_copied,
    feed_url_copy_failed and embed_copy_blocked — from
    templates/calendars/_add_to_calendar.html.
    """

    # Signup and setup
    USER_SIGNED_UP = "user_signed_up"
    CALENDAR_CREATED = "calendar_created"
    SOURCE_ADDED = "source_added"

    # Onboarding friction
    SOURCE_VALIDATION_FAILED = "source_validation_failed"
    TIER_LIMIT_HIT = "tier_limit_hit"
    TIER_FEATURE_DENIED = "tier_feature_denied"

    # Upgrade path
    PRICING_VIEWED = "pricing_viewed"
    CHECKOUT_COMPLETED = "checkout_completed"
    SUBSCRIPTION_TIER_CHANGED = "subscription_tier_changed"
    SUBSCRIPTION_ENDED = "subscription_ended"


def source_domain(url: str) -> str | None:
    """Return the host of a source URL, the part that is safe to send."""
    return urlparse(url).netloc or None


def capture(
    event: str,
    *,
    user: User | None = None,
    distinct_id: str | None = None,
    **properties: Any,
) -> None:
    """Send a product event, unless no PostHog project is configured.

    Pass `user` from webhooks and background tasks, where there is no request
    context to identify the person. Within a request, leave it off.
    """
    if not settings.POSTHOG_API_KEY:
        return

    if distinct_id is None and user is not None:
        distinct_id = str(user.pk)

    kwargs: dict[str, Any] = {
        "properties": {k: v for k, v in properties.items() if v is not None},
    }
    if distinct_id is not None:
        kwargs["distinct_id"] = distinct_id

    try:
        posthog.capture(event, **kwargs)
    except Exception:  # noqa: BLE001
        # Analytics must never break the thing it is measuring. Warning rather
        # than exception: a PostHog outage should not page us through Sentry.
        logger.warning("PostHog capture failed for %s", event, exc_info=True)


def set_person_properties(user: User, **properties: Any) -> None:
    """Set properties on a person profile, for cohorts and flag targeting."""
    if not settings.POSTHOG_API_KEY:
        return

    try:
        posthog.set(
            distinct_id=str(user.pk),
            properties={k: v for k, v in properties.items() if v is not None},
        )
    except Exception:  # noqa: BLE001
        logger.warning("PostHog set failed for user %s", user.pk, exc_info=True)
