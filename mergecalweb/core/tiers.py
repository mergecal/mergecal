"""Single source of truth for subscription-tier entitlements.

Which tier a user is on is decided by billing (Stripe webhooks); what a
tier allows is decided here. Models expose these rules through their
existing properties (``User.can_*``, ``Calendar.can_add_source``).
"""

from __future__ import annotations

from django.db.models import TextChoices

UNLIMITED = float("inf")


class SubscriptionTier(TextChoices):
    FREE = "free_tier", "Free Tier"
    PERSONAL = "personal_tier", "Personal Tier"
    BUSINESS = "business_tier", "Business Tier"
    SUPPORTER = "supporter_tier", "Supporter Tier"


# Tiers entitled to premium features: custom update frequency, branding
# removal, and per-source customization.
PREMIUM_TIERS = frozenset(
    {
        SubscriptionTier.BUSINESS,
        SubscriptionTier.SUPPORTER,
    },
)

# Unknown or legacy tier values fall back to the most restrictive limit.
_NO_ACCESS = 0

CALENDAR_LIMITS: dict[str, float] = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.PERSONAL: 2,
    SubscriptionTier.BUSINESS: 5,
    SubscriptionTier.SUPPORTER: UNLIMITED,
}

SOURCE_LIMITS: dict[str, float] = {
    SubscriptionTier.FREE: 0,
    SubscriptionTier.PERSONAL: 3,
    SubscriptionTier.BUSINESS: 5,
    SubscriptionTier.SUPPORTER: UNLIMITED,
}


def has_premium_features(tier: str) -> bool:
    return tier in PREMIUM_TIERS


def calendar_limit(tier: str) -> float:
    return CALENDAR_LIMITS.get(tier, _NO_ACCESS)


def source_limit(tier: str) -> float:
    return SOURCE_LIMITS.get(tier, _NO_ACCESS)
