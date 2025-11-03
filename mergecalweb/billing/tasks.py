import logging

from celery import shared_task
from djstripe.models import Customer

from config import celery_app
from mergecalweb.billing.signals import update_user_subscription_tier
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def update_stripe_subscription(self, user_id: int) -> None:
    """
    Update user's stripe subscription based on subscription_tier.
    """
    user: User = User.objects.get(id=user_id)
    customer: Customer = user.djstripe_customers.first()
    if not customer:
        logger.warning(
            "User missing Stripe customer during subscription update",
            extra={
                "event": LogEvent.BILLING_ERROR,
                "error_type": "no-customer",
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
            },
        )
        return

    subscription = customer.subscriptions.filter(
        status__in=["active", "trialing"],
    ).first()
    if not subscription:
        logger.warning(
            "User missing active Stripe subscription during update",
            extra={
                "event": LogEvent.BILLING_ERROR,
                "error_type": "no-subscription",
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
                "customer_id": customer.id,
            },
        )
        return

    logger.info(
        "Updating user subscription tier from Stripe data",
        extra={
            "event": LogEvent.SUBSCRIPTION_SYNC,
            "status": "start",
            "user_id": user_id,
            "email": user.email,
            "customer_id": customer.id,
            "subscription_id": subscription.id,
            "subscription_status": subscription.status,
        },
    )

    update_user_subscription_tier(user, subscription)


@shared_task
def update_all_users_from_stripe_customers() -> None:
    """
    Loop through all Stripe Customers and trigger the update_stripe_subscription task
    for each associated user.
    """
    total_customers = Customer.objects.count()
    processed = 0
    errors = 0

    logger.info(
        "Starting bulk Stripe subscription sync",
        extra={
            "event": LogEvent.SUBSCRIPTION_SYNC,
            "status": "start",
            "total_customers": total_customers,
        },
    )

    for customer in Customer.objects.all():
        try:
            user = customer.subscriber
            if isinstance(user, User):
                update_stripe_subscription.delay(user.id)
                logger.debug(
                    "Queued subscription update task for user",
                    extra={
                        "event": LogEvent.SUBSCRIPTION_SYNC,
                        "user_id": user.id,
                        "customer_id": customer.id,
                    },
                )
                processed += 1
            else:
                logger.warning(
                    "Stripe customer subscriber is not a User",
                    extra={
                        "event": LogEvent.SUBSCRIPTION_SYNC,
                        "customer_id": customer.id,
                        "subscriber_type": type(user).__name__,
                    },
                )
        except Exception:
            logger.exception(
                "Error processing Stripe customer during bulk sync",
                extra={
                    "event": LogEvent.SUBSCRIPTION_SYNC,
                    "customer_id": customer.id,
                },
            )
            errors += 1

    logger.info(
        "Completed bulk Stripe subscription sync",
        extra={
            "event": LogEvent.SUBSCRIPTION_SYNC,
            "status": "complete",
            "total_customers": total_customers,
            "processed": processed,
            "errors": errors,
        },
    )


@shared_task
def schedule_follow_up_email(user_id: int) -> None:
    """
    Schedule follow-up email to be sent 3 days after user signup.
    Uses Celery countdown to delay execution.
    """
    send_follow_up_email_delayed.apply_async(
        (user_id,),
        countdown=3 * 24 * 60 * 60,  # 3 days in seconds
    )
    logger.info(
        "Scheduled follow-up email for 3 days from now",
        extra={
            "event": "follow_up_email_scheduled",
            "user_id": user_id,
        },
    )


@shared_task
def send_follow_up_email_delayed(user_id: int) -> None:
    """
    Send follow-up email 3 days after signup.
    Only sends if user is still on a paid tier (hasn't canceled).
    """
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        logger.warning(
            "User not found for follow-up email",
            extra={
                "event": "follow_up_email_user_not_found",
                "user_id": user_id,
            },
        )
        return

    # Check if user is still on a paid tier
    if user.subscription_tier == User.SubscriptionTier.FREE:
        logger.info(
            "Skipping follow-up email - user is on free tier",
            extra={
                "event": "follow_up_email_skipped_free_tier",
                "user_id": user_id,
                "username": user.username,
            },
        )
        return

    # Send the follow-up email
    # send_follow_up_email(user) # noqa: ERA001

    logger.info(
        "Sent follow-up email to user",
        extra={
            "event": "follow_up_email_sent",
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "subscription_tier": user.subscription_tier,
            "active": False,
        },
    )
