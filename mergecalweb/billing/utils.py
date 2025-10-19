import logging

from djstripe.models import Customer  # noqa: TC002
from djstripe.models import Subscription  # noqa: TC002

from mergecalweb.billing.signals import update_user_subscription_tier
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


def sync_user_tier_with_stripe(user: User) -> dict[str, str | None]:
    """
    Sync a user's subscription tier with their Stripe subscription.

    Args:
        user: The User instance to sync

    Returns:
        dict with keys:
            - status: "synced", "no_customer", "no_subscription"
            - message: Human-readable message about what happened
            - customer_id: Stripe customer ID if found, None otherwise
            - subscription_id: Stripe subscription ID if found, None otherwise
    """
    customer: Customer | None = user.djstripe_customers.first()
    if not customer:
        return {
            "status": "no_customer",
            "message": f"User {user.username} has no Stripe customer",
            "customer_id": None,
            "subscription_id": None,
        }

    subscription: Subscription | None = customer.subscriptions.filter(
        status__in=["active", "trialing", "past_due"],
    ).first()

    if not subscription:
        # No active subscription, set to free tier
        old_tier = user.subscription_tier
        if user.subscription_tier != User.SubscriptionTier.FREE:
            user.subscription_tier = User.SubscriptionTier.FREE
            user.save()
            msg = f"User {user.username} downgraded to FREE tier (was {old_tier})"
            return {
                "status": "synced",
                "message": msg,
                "customer_id": customer.id,
                "subscription_id": None,
            }
        msg = f"User {user.username} has no active subscription, already FREE tier"
        return {
            "status": "no_subscription",
            "message": msg,
            "customer_id": customer.id,
            "subscription_id": None,
        }

    # Sync tier with subscription
    old_tier = user.subscription_tier
    update_user_subscription_tier(user, subscription)
    user.refresh_from_db()
    new_tier = user.subscription_tier

    if old_tier != new_tier:
        message = f"User {user.username} tier updated from {old_tier} to {new_tier}"
    else:
        message = f"User {user.username} tier already synced ({new_tier})"

    return {
        "status": "synced",
        "message": message,
        "customer_id": customer.id,
        "subscription_id": subscription.id,
    }
