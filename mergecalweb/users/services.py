"""User account management services."""

import logging
from typing import TYPE_CHECKING
from typing import TypedDict

from django.db import transaction
from django.utils import timezone

from mergecalweb.core.logging_events import LogEvent
from mergecalweb.users.models import User

if TYPE_CHECKING:
    from djstripe.models import Customer

logger = logging.getLogger(__name__)


class DeletionStats(TypedDict):
    """Statistics returned from account deletion."""

    calendar_count: int
    source_count: int
    deleted_at: str
    user_email: str
    user_username: str


def delete_user_account(user: User) -> DeletionStats:
    """
    Delete a user account and all associated data.

    This function:
    1. Collects deletion statistics
    2. Cancels active Stripe subscriptions
    3. Marks Stripe customer as deleted (without deleting the customer record)
    4. Deletes the user (CASCADE handles calendars and sources)
    5. Returns statistics for confirmation email

    Args:
        user: User instance to delete

    Returns:
        DeletionStats: Dictionary with deletion statistics

    Raises:
        Any unexpected exceptions bubble up to Sentry for tracking
    """
    user_id = user.pk
    user_email = user.email
    user_username = user.username

    logger.info(
        "Starting account deletion process",
        extra={
            "event": LogEvent.ACCOUNT_DELETION_STARTED,
            "user_id": user_id,
            "username": user_username,
            "email": user_email,
        },
    )

    # 1. Collect deletion statistics before deletion
    calendar_count = user.calendar_set.count()
    source_count = sum(
        calendar.calendarOf.count() for calendar in user.calendar_set.all()
    )

    logger.debug(
        "Collected deletion statistics",
        extra={
            "event": LogEvent.ACCOUNT_DELETION_STATS,
            "user_id": user_id,
            "username": user_username,
            "calendar_count": calendar_count,
            "source_count": source_count,
        },
    )

    # 2. Handle Stripe subscriptions and customer
    customer: Customer | None = user.djstripe_customers.first()

    if customer:
        logger.info(
            "Found Stripe customer for deletion",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_STRIPE_CUSTOMER,
                "user_id": user_id,
                "username": user_username,
                "customer_id": customer.id,
            },
        )

        # Cancel active subscriptions
        active_subscriptions = customer.subscriptions.filter(
            status__in=["active", "trialing", "past_due"],
        )
        subscription_count = active_subscriptions.count()

        for subscription in active_subscriptions:
            logger.info(
                "Canceling Stripe subscription",
                extra={
                    "event": LogEvent.ACCOUNT_DELETION_SUBSCRIPTION_CANCEL,
                    "user_id": user_id,
                    "username": user_username,
                    "subscription_id": subscription.id,
                    "subscription_status": subscription.status,
                },
            )
            subscription.cancel()

        # Mark customer as deleted (retain for financial records)
        deleted_at = timezone.now().isoformat()
        customer.metadata["account_deleted"] = "true"
        customer.metadata["deleted_at"] = deleted_at
        customer.save()

        logger.info(
            "Updated Stripe customer metadata",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_STRIPE_UPDATED,
                "user_id": user_id,
                "username": user_username,
                "customer_id": customer.id,
                "subscriptions_canceled": subscription_count,
            },
        )
    else:
        logger.debug(
            "No Stripe customer found for user",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_NO_STRIPE,
                "user_id": user_id,
                "username": user_username,
            },
        )
        deleted_at = timezone.now().isoformat()

    # 3. Delete user (CASCADE handles calendars and sources)
    with transaction.atomic():
        user.delete()

    logger.info(
        "Account deletion completed successfully",
        extra={
            "event": LogEvent.ACCOUNT_DELETED,
            "user_id": user_id,
            "username": user_username,
            "email": user_email,
            "calendar_count": calendar_count,
            "source_count": source_count,
        },
    )

    # 4. Return statistics
    return DeletionStats(
        calendar_count=calendar_count,
        source_count=source_count,
        deleted_at=deleted_at,
        user_email=user_email,
        user_username=user_username,
    )
