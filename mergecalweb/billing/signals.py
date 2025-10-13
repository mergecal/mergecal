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
from mergecalweb.core.logging_events import LogEvent
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
        old_tier = user.subscription_tier
        user.subscription_tier = new_tier
        user.save()
        logger.info(
            "Subscription tier changed",
            extra={
                "event": LogEvent.SUBSCRIPTION_TIER_CHANGE,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "old_tier": old_tier,
                "new_tier": new_tier,
                "subscription_status": subscription.status,
                "plan_name": subscription.plan.product.name,
            },
        )
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
    customers = Customer.objects.filter(email=user.email)
    for customer in customers:
        if not customer.subscriber:
            logger.warning(
                "Orphaned Stripe customer attached to user",
                extra={
                    "event": LogEvent.STRIPE_CUSTOMER_ATTACHED,
                    "customer_id": customer.id,
                    "user_id": user.pk,
                    "username": user.username,
                    "email": user.email,
                },
            )
            customer.subscriber = user
            customer.save()
    if not customers:
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
                "Stripe customer created with trial subscription",
                extra={
                    "event": LogEvent.STRIPE_CUSTOMER_CREATED,
                    "user_id": user.pk,
                    "username": user.username,
                    "email": user.email,
                    "customer_id": customer.id,
                    "plan": price.lookup_key,
                    "trial_days": 14,
                },
            )


@djstripe_receiver("customer.subscription.trial_will_end")
def handle_trial_will_end(sender: Any, event: Event, **kwargs: dict[str, Any]) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)

    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Trial ending webhook received for customer without user",
            extra={
                "event": LogEvent.TRIAL_ENDING_NO_USER,
                "customer_id": customer_id,
                "webhook_type": event.type,
            },
        )
        return

    logger.info(
        "Trial ending soon, sending reminder email",
        extra={
            "event": LogEvent.TRIAL_ENDING,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "customer_id": customer_id,
        },
    )

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
    user: User | None = customer.subscriber

    logger.info(
        "Checkout session completed",
        extra={
            "event": LogEvent.CHECKOUT_COMPLETED,
            "customer_id": customer_id,
            "user_id": user.pk if user else None,
            "username": user.username if user else None,
            "email": user.email if user else None,
        },
    )
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
            "Subscription webhook received for customer without user",
            extra={
                "event": LogEvent.SUBSCRIPTION_UPDATE_NO_USER,
                "customer_id": customer_id,
                "subscription_id": subscription.id,
                "subscription_status": subscription.status,
                "webhook_type": event.type,
            },
        )
        return

    logger.info(
        "Subscription webhook received, updating user tier",
        extra={
            "event": LogEvent.SUBSCRIPTION_UPDATE,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "customer_id": customer_id,
            "subscription_id": subscription.id,
            "subscription_status": subscription.status,
            "webhook_type": event.type,
        },
    )

    update_user_subscription_tier(user, subscription)


@djstripe_receiver("customer.subscription.deleted")
@djstripe_receiver("customer.subscription.paused")
def handle_subscription_end(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    customer_id: str = event.data["object"]["customer"]
    customer: Customer = Customer.objects.get(id=customer_id)
    user: User | None = customer.subscriber

    if not user:
        logger.warning(
            "Subscription end webhook received for customer without user",
            extra={
                "event": LogEvent.SUBSCRIPTION_END_NO_USER,
                "customer_id": customer_id,
                "webhook_type": event.type,
            },
        )
        return

    old_tier = user.subscription_tier
    user.subscription_tier = User.SubscriptionTier.FREE
    user.save()

    logger.info(
        "Subscription ended, user downgraded to free tier",
        extra={
            "event": LogEvent.SUBSCRIPTION_ENDED,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "customer_id": customer_id,
            "old_tier": old_tier,
            "new_tier": User.SubscriptionTier.FREE,
            "webhook_type": event.type,
        },
    )


@djstripe_receiver("invoice.created")
@djstripe_receiver("invoice.finalized")
@djstripe_receiver("invoice.payment_failed")
@djstripe_receiver("invoice.payment_action_required")
@djstripe_receiver("invoice.paid")
def handle_invoice_events(sender: Any, event: Event, **kwargs: dict[str, Any]) -> None:
    invoice_id: str = event.data["object"]["id"]
    invoice: Invoice = Invoice.objects.get(id=invoice_id)
    customer: Customer = invoice.customer
    user: User | None = customer.subscriber

    if not user:
        logger.warning(
            "Invoice webhook received for customer without user",
            extra={
                "event": LogEvent.INVOICE_EVENT_NO_USER,
                "customer_id": customer.id,
                "invoice_id": invoice_id,
                "webhook_type": event.type,
            },
        )
        return

    if event.type == "invoice.paid":
        subscription: Subscription = invoice.subscription
        logger.info(
            "Invoice paid successfully",
            extra={
                "event": LogEvent.INVOICE_PAID,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "customer_id": customer.id,
                "invoice_id": invoice_id,
                "subscription_id": subscription.id,
                "amount_paid": invoice.amount_paid,
                "currency": invoice.currency,
            },
        )
        # Handle successful payment
        update_user_subscription_tier(user, subscription)
    elif event.type in [
        "invoice.payment_failed",
        "invoice.payment_action_required",
    ]:
        old_tier = user.subscription_tier
        logger.warning(
            "Invoice payment failed, downgrading to free tier",
            extra={
                "event": LogEvent.INVOICE_PAYMENT_FAILED,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "customer_id": customer.id,
                "invoice_id": invoice_id,
                "old_tier": old_tier,
                "webhook_type": event.type,
                "amount_due": invoice.amount_due,
                "currency": invoice.currency,
            },
        )
        # Handle failed payment
        user.subscription_tier = User.SubscriptionTier.FREE
        user.save()
    else:
        # For invoice.created, invoice.finalized
        logger.info(
            "Invoice event received",
            extra={
                "event": LogEvent.INVOICE_EVENT,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "customer_id": customer.id,
                "invoice_id": invoice_id,
                "webhook_type": event.type,
                "amount_due": invoice.amount_due,
                "currency": invoice.currency,
            },
        )


@djstripe_receiver("payment_method.attached")
def handle_payment_method_attached(
    sender: Any,
    event: Event,
    **kwargs: dict[str, Any],
) -> None:
    payment_method_id: str = event.data["object"]["id"]
    payment_method: PaymentMethod = PaymentMethod.objects.get(id=payment_method_id)
    customer: Customer | None = payment_method.customer

    if not customer:
        logger.warning(
            "Payment method attached but customer not found",
            extra={
                "event": LogEvent.PAYMENT_METHOD_NO_CUSTOMER,
                "payment_method_id": payment_method_id,
                "payment_method_type": payment_method.type,
            },
        )
        return

    user: User | None = customer.subscriber
    if not user:
        logger.warning(
            "Payment method attached but user not found for customer",
            extra={
                "event": LogEvent.PAYMENT_METHOD_NO_USER,
                "payment_method_id": payment_method_id,
                "customer_id": customer.id,
                "payment_method_type": payment_method.type,
            },
        )
        return

    card_brand = payment_method.card.brand if payment_method.card else None
    card_last4 = payment_method.card.last4 if payment_method.card else None

    logger.info(
        "Payment method attached to customer",
        extra={
            "event": LogEvent.PAYMENT_METHOD_ATTACHED,
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "customer_id": customer.id,
            "payment_method_id": payment_method_id,
            "payment_method_type": payment_method.type,
            "payment_method_brand": card_brand,
            "payment_method_last4": card_last4,
        },
    )

    with sentry_sdk.configure_scope() as scope:
        scope.set_tag("payment_method", "attached")
        if user:
            scope.set_user({"id": user.pk, "email": user.email})
        sentry_sdk.capture_message(
            "Payment method attached",
            level="info",
        )
