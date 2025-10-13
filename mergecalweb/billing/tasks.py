from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from djstripe.models import Customer

from config import celery_app
from mergecalweb.billing.signals import update_user_subscription_tier

logger = get_task_logger(__name__)
User = get_user_model()


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
                "event": "subscription_update_no_customer",
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
                "event": "subscription_update_no_subscription",
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
            "event": "subscription_update_task",
            "user_id": user_id,
            "username": user.username,
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
            "event": "bulk_subscription_sync_start",
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
                        "event": "subscription_sync_queued",
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
                        "event": "subscription_sync_invalid_subscriber",
                        "customer_id": customer.id,
                        "subscriber_type": type(user).__name__,
                    },
                )
        except Exception:
            logger.exception(
                "Error processing Stripe customer during bulk sync",
                extra={
                    "event": "subscription_sync_error",
                    "customer_id": customer.id,
                },
            )
            errors += 1

    logger.info(
        "Completed bulk Stripe subscription sync",
        extra={
            "event": "bulk_subscription_sync_complete",
            "total_customers": total_customers,
            "processed": processed,
            "errors": errors,
        },
    )
