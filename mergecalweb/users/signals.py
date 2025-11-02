"""User-related signals for handling signup and lifecycle events."""

import logging

from allauth.account.signals import user_signed_up
from django.dispatch import receiver

from mergecalweb.billing.emails import send_welcome_email
from mergecalweb.billing.tasks import schedule_follow_up_email
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


@receiver(user_signed_up)
def handle_new_user_signup(sender, request, user, **kwargs):
    """
    Handle new user signup via allauth.
    Send welcome email and schedule follow-up email for 3 days later.
    """
    logger.info(
        "New user signed up",
        extra={
            "event": "user_signup",
            "user_id": user.id,
            "username": user.username,
            "email": user.email,
        },
    )

    # Send welcome email immediately
    # Note: We send for Business tier as that's what trial starts with
    send_welcome_email(user, User.SubscriptionTier.BUSINESS)

    # Schedule follow-up email for 3 days from now
    schedule_follow_up_email.delay(user.id)
