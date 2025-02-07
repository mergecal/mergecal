# ruff: noqa: ERA001
import logging
from typing import Any

import sentry_sdk
import stripe
from django.conf import settings
from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver
from django.http import HttpRequest
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Customer
from djstripe.models import Event
from djstripe.models import Invoice
from djstripe.models import PaymentMethod
from djstripe.models import Price
from djstripe.models import Subscription

from mergecalweb.billing.emails import send_trial_ending_email
from mergecalweb.billing.emails import upgrade_subscription_email
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY


def update_user_subscription_tier(user: User, subscription: Subscription) -> None:
    new_tier = None
    if subscription.status in ["active", "trialing"]:
        match subscription.plan.product.name:
            case User.SubscriptionTier.PERSONAL.label:
                new_tier = User.SubscriptionTier.PERSONAL
            case User.SubscriptionTier.BUSINESS.label:
                new_tier = User.SubscriptionTier.BUSINESS
            case User.SubscriptionTier.SUPPORTER.label:
                new_tier = User.SubscriptionTier.SUPPORTER
    else:
        new_tier = User.SubscriptionTier.FREE

    if user.subscription_tier != new_tier:
        # old_tier = user.subscription_tier
        user.subscription_tier = new_tier
        user.save()
        logger.info("User %s has been updated to %s tier", user, new_tier)
        if new_tier != User.SubscriptionTier.FREE:
            email = upgrade_subscription_email(user, new_tier)
            email.send()
            # elif old_tier != User.SubscriptionTier.FREE:
            #     # Optionally send a downgrade email
            #     email = downgrade_subscription_email(user)
            #     email.send()


@receiver(signal=user_logged_in)
def create_stripe_customer(
    sender: Any,
    request: HttpRequest,
    user: User,
    **kwargs: dict[str, Any],
) -> None:
    try:
        customers = Customer.objects.filter(email=user.email)
        for customer in customers:
            if not customer.subscriber:
                logger.warning(
                    "Stripe Customer %s without subscriber attaching to user: %s",
                    customer,
                    user,
                )
                customer.subscriber = user
                customer.save()
    except Customer.DoesNotExist:
        customer, created = Customer.get_or_create(subscriber=user)
        if created:
            price = Price.objects.get(lookup_key="business_monthly")
            stripe.Subscription.create(
                customer=customer.id,
                items=[{"price": price.id}],
                trial_period_days=14,
                payment_settings={"save_default_payment_method": "on_subscription"},
                trial_settings={"end_behavior": {"missing_payment_method": "cancel"}},
            )
            # coupon = Coupon.objects.get(name="beta")
            # customer.add_coupon(coupon)
            logger.info(
                "Stripe customer created for user: %s and added to plan: %s",
                user,
                price,
            )


@djstripe_receiver("customer.subscription.trial_will_end")
def handle_trial_will_end(sender: Any, event: Event, **kwargs: dict[str, Any]) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    logger.info("Subscription trial will end soon for customer: %s", customer)

    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Subscriber not found for customer: %s, skipping trial ending email",
            customer,
        )
        return

    email = send_trial_ending_email(user)
    email.send()
    # Send email to customer


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    # subscription: Subscription = Subscription.objects.get(
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
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    subscription: Subscription = Subscription.objects.get(
        id=event.data["object"]["id"],
    )
    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Subscriber/User not found for customer: %s, skipping updating user tier",
            customer,
        )
        return

    update_user_subscription_tier(user, subscription)


@djstripe_receiver("customer.subscription.deleted")
@djstripe_receiver("customer.subscription.paused")
def handle_subscription_end(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    logger.info("Webhook Event Type: %s", event.type)
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Subscriber/User not found for customer: %s, skipping updating user to free tier",  # noqa: E501
            customer,
        )
        return

    user.subscription_tier = User.SubscriptionTier.FREE
    user.save()
    logger.info("Subscription ended for customer: %s", customer)


@djstripe_receiver("invoice.created")
@djstripe_receiver("invoice.finalized")
@djstripe_receiver("invoice.payment_failed")
@djstripe_receiver("invoice.payment_action_required")
@djstripe_receiver("invoice.paid")
def handle_invoice_events(sender: Any, event: Event, **kwargs: dict[str, Any]) -> None:
    logger.info("Invoice Event Type: %s", event.type)
    invoice_id: str = event.data["object"]["id"]
    invoice: Invoice = Invoice.objects.get(id=invoice_id)
    customer: Customer = invoice.customer
    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Subscriber/User not found for customer: %s, skipping handling invoice event",  # noqa: E501
            customer,
        )
        return

    if event.type == "invoice.paid":
        logger.info("Invoice paid for user: %s", user)
        # Handle successful payment
        subscription: Subscription = invoice.subscription
        update_user_subscription_tier(user, subscription)
    elif event.type in [
        "invoice.payment_failed",
        "invoice.payment_action_required",
    ]:
        logger.info("Invoice payment failed for user: %s", user)
        # Handle failed payment
        user.subscription_tier = User.SubscriptionTier.FREE
        user.save()
    logger.info("Invoice event handled for user: %s", user)


@djstripe_receiver("payment_method.attached")
def handle_payment_method_attached(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    logger.info("Invoice Event Type: %s", event.type)
    payment_method_id: str = event.data["object"]["id"]
    payment_method: PaymentMethod = PaymentMethod.objects.get(id=payment_method_id)
    customer: Customer | None = payment_method.customer
    if not customer:
        logger.exception(
            "Customer not found for payment method: %s, skipping handling payment method attached",  # noqa: E501
            payment_method,
        )
        return
    user: User | None = customer.subscriber
    if not user:
        logger.exception(
            "Subscriber/User not found for customer: %s, skipping handling payment method attached",  # noqa: E501
            customer,
        )

    logger.info("Payment method attached for user: %s", user)

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("payment_method", "attached")
        if user:
            scope.set_user({"id": user.pk, "email": user.email})
        sentry_sdk.capture_message(
            "Payment method attached",
            level="info",
        )
