from celery import shared_task
from celery.utils.log import get_task_logger
from django.contrib.auth import get_user_model
from djstripe.models import Customer

from config import celery_app
from mergecal.billing.signals import update_user_subscription_tier

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
        logger.warning("User %s does not have a stripe customer.", user_id)
        return

    subscription = customer.subscriptions.filter(
        status__in=["active", "trialing"],
    ).first()
    if not subscription:
        logger.warning("User %s does not have a stripe subscription.", user_id)
        return

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

    for customer in Customer.objects.all():
        try:
            user = customer.subscriber
            if isinstance(user, User):
                update_stripe_subscription.delay(user.id)
                logger.info(
                    "Triggered update for user %s associated with Stripe customer %s",
                    user.id,
                    customer.id,
                )
                processed += 1
            else:
                logger.warning(
                    "Subscriber for Stripe customer %s is not a User instance",
                    customer.id,
                )
        except Exception:
            logger.exception(
                "Error processing Stripe customer %s",
                customer.id,
            )
            errors += 1

    logger.info(
        "Processed %s out of %s customers. Errors: %s",
        processed,
        total_customers,
        errors,
    )
