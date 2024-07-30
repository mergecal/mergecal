import logging
from typing import Any

from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpRequest
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Customer
from djstripe.models import Event
from djstripe.models import Invoice
from djstripe.models import Subscription

from mergecal.users.models import User

logger = logging.getLogger(__name__)


def update_user_subscription_tier(user: User, subscription: Subscription) -> None:
    new_tier = None
    if subscription.status in ["active", "trialing"]:
        logger.info("Updating subscription tier for user: %s", user)
        if subscription.plan.product.name.lower() == "basic":
            new_tier = User.SubscriptionTier.BASIC
        elif subscription.plan.product.name.lower() == "premium":
            new_tier = User.SubscriptionTier.PREMIUM
        elif subscription.plan.product.name.lower() == "elite":
            new_tier = User.SubscriptionTier.ELITE
    else:
        new_tier = User.SubscriptionTier.NONE

    if user.subscription_tier != new_tier:
        user.subscription_tier = new_tier
        user.save()
        logger.info("User %s has been updated to %s tier", user, new_tier)
    else:
        logger.info("No change in subscription tier for user: %s", user)


@receiver(signal=user_logged_in)
def create_stripe_customer(
    sender: Any,
    request: HttpRequest,
    user: User,
    **kwargs: dict[str, Any],
) -> None:
    customer, created = Customer.get_or_create(subscriber=user)


@djstripe_receiver("customer.subscription.trial_will_end")
def handle_trial_will_end(sender: Any, event: Event, **kwargs: dict[str, Any]) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    logger.info("Subscription trial will end soon for customer: %s", customer)
    # Send email to customer


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    logger.info("Checkout session completed for customer: %s", customer)
    # Send email to customer


@djstripe_receiver("customer.subscription.created")
@djstripe_receiver("customer.subscription.resumed")
@djstripe_receiver("customer.subscription.updated")
def handle_subscription_update(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    logger.info("Webhook Event Type: %s", event.type)
    customer_id: str = event.data["object"]["customer"]
    try:
        customer: Customer = Customer.objects.get(id=customer_id)
        subscription: Subscription = Subscription.objects.get(
            id=event.data["object"]["id"],
        )
        user: User = customer.subscriber
        update_user_subscription_tier(user, subscription)
        logger.info("Subscription updated for customer: %s", customer)
    except (Customer.DoesNotExist, Subscription.DoesNotExist):
        logger.exception("Customer or Subscription not found")


@djstripe_receiver("customer.subscription.deleted")
@djstripe_receiver("customer.subscription.paused")
def handle_subscription_end(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    logger.info("Webhook Event Type: %s", event.type)
    customer_id: str = event.data["object"]["customer"]
    try:
        customer: Customer = Customer.objects.get(id=customer_id)
        user: User = customer.subscriber
        user.subscription_tier = User.SubscriptionTier.NONE
        user.save()
        logger.info("Subscription ended for customer: %s", customer)
    except Customer.DoesNotExist:
        logger.exception("Customer not found")


@djstripe_receiver("invoice.created")
@djstripe_receiver("invoice.finalized")
@djstripe_receiver("invoice.payment_failed")
@djstripe_receiver("invoice.payment_action_required")
@djstripe_receiver("invoice.paid")
def handle_invoice_events(sender: Any, **kwargs: dict[str, Any]) -> None:
    event: Event = kwargs.get("event")
    logger.info("Invoice Event Type: %s", event.type)
    invoice_id: str = event.data["object"]["id"]
    try:
        invoice: Invoice = Invoice.objects.get(id=invoice_id)
        customer: Customer = invoice.customer
        user: User = customer.subscriber
        if event.type == "invoice.paid":
            # Handle successful payment
            subscription: Subscription = invoice.subscription
            update_user_subscription_tier(user, subscription)
        elif event.type in [
            "invoice.payment_failed",
            "invoice.payment_action_required",
        ]:
            # Handle failed payment
            user.subscription_tier = User.SubscriptionTier.NONE
            user.save()
        logger.info("Invoice event handled for user: %s", user)
    except (Invoice.DoesNotExist, Customer.DoesNotExist):
        logger.exception("Invoice or Customer not found:")