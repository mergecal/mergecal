from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from djstripe.models import Customer

from config import celery_app
from mergecalweb.billing.utils import sync_user_tier_with_stripe
from mergecalweb.core.logging_events import LogEvent

logger = get_task_logger(__name__)
User = get_user_model()


@celery_app.task(bind=True)
def update_stripe_subscription(self, user_id: int) -> None:
    """
    Update user's stripe subscription based on subscription_tier.
    """
    user: User = User.objects.get(id=user_id)
    result = sync_user_tier_with_stripe(user)

    if result["status"] == "no_customer":
        logger.warning(
            "User missing Stripe customer during subscription update",
            extra={
                "event": LogEvent.SUBSCRIPTION_UPDATE_NO_CUSTOMER,
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
            },
        )
        return

    if result["status"] == "no_subscription":
        logger.warning(
            "User missing active Stripe subscription during update",
            extra={
                "event": LogEvent.SUBSCRIPTION_UPDATE_NO_SUBSCRIPTION,
                "user_id": user_id,
                "username": user.username,
                "email": user.email,
                "customer_id": result["customer_id"],
            },
        )
        return

    logger.info(
        "Updated user subscription tier from Stripe data",
        extra={
            "event": LogEvent.SUBSCRIPTION_UPDATE_TASK,
            "user_id": user_id,
            "username": user.username,
            "email": user.email,
            "customer_id": result["customer_id"],
            "subscription_id": result["subscription_id"],
            "sync_message": result["message"],
        },
    )


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
            "event": LogEvent.BULK_SUBSCRIPTION_SYNC_START,
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
                        "event": LogEvent.SUBSCRIPTION_SYNC_QUEUED,
                        "user_id": user.id,
                        "username": user.username,
                        "customer_id": customer.id,
                    },
                )
                processed += 1
            else:
                logger.warning(
                    "Stripe customer subscriber is not a User",
                    extra={
                        "event": LogEvent.SUBSCRIPTION_SYNC_INVALID_SUBSCRIBER,
                        "customer_id": customer.id,
                        "subscriber_type": type(user).__name__,
                    },
                )
        except Exception:
            logger.exception(
                "Error processing Stripe customer during bulk sync",
                extra={
                    "event": LogEvent.SUBSCRIPTION_SYNC_ERROR,
                    "customer_id": customer.id,
                },
            )
            errors += 1

    logger.info(
        "Completed bulk Stripe subscription sync",
        extra={
            "event": LogEvent.BULK_SUBSCRIPTION_SYNC_COMPLETE,
            "total_customers": total_customers,
            "processed": processed,
            "errors": errors,
        },
    )
