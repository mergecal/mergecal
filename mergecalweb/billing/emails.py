"""Billing-related email notifications."""

import logging

from django.urls import reverse
from django.utils import timezone

from mergecalweb.core.emails import send_email
from mergecalweb.core.utils import get_site_url
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


def send_welcome_email(user: User, tier: User.SubscriptionTier) -> int:
    """Send welcome email for new users starting trial."""
    subject = f"Welcome to MergeCal {tier.label}!"

    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")

    bodies = [
        f"Welcome to MergeCal! Your 14-day trial of {tier.label} has started.",
        (
            f"Get started by visiting your "
            f'<a href="{account_url}">calendar management page</a>. '
            "You can add calendars from Google, Apple, Microsoft, and any iCal feed."
        ),
        "If you have any questions, just reply to this email.",
    ]

    ps = "I'm here to help you get the most out of MergeCal."

    return send_email(
        to_users=[user],
        subject=subject,
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
    )


def send_follow_up_email(user: User) -> int:
    """Send follow-up email 3 days after signup."""
    subject = "Getting the most out of MergeCal"

    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")

    bodies = [
        (
            "You're a few days into using MergeCal. "
            "Here are some tips to get the most out of it:"
        ),
        (
            f"Make sure you've added all your calendars in your "
            f'<a href="{account_url}">calendar dashboard</a>. '
            "The more calendars you combine, the more useful MergeCal becomes."
        ),
        (
            "Remember, your combined calendar updates automatically when "
            "events change in any of your source calendars."
        ),
        (
            "If you're running into any issues or have questions, "
            "just reply to this email."
        ),
    ]

    return send_email(
        to_users=[user],
        subject=subject,
        bodies=bodies,
        from_email="Abe <abe@mergecal.org>",
    )


def upgrade_subscription_email(
    user: User,
    tier: User.SubscriptionTier,
) -> int:
    """
    Send subscription upgrade/change confirmation email.
    Skips sending if user just signed up (within 1 hour) since welcome
    email was already sent via signup signal.
    """
    # Check if user signed up recently (within 1 hour)
    one_hour_seconds = 3600
    time_since_signup = timezone.now() - user.date_joined
    is_new_user = time_since_signup.total_seconds() < one_hour_seconds

    if is_new_user:
        # Welcome email already sent via allauth signup signal
        logger.info(
            "Skipping subscription email for new user (welcome already sent)",
            extra={
                "event": "subscription_email_skipped_new_user",
                "user_id": user.id,
                "username": user.username,
                "tier": tier,
            },
        )
        return 0

    # Existing user changing subscription
    subject = f"Your MergeCal {tier.label} subscription is active"

    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")

    bodies = {
        User.SubscriptionTier.PERSONAL: [
            (
                f"Your upgrade to MergeCal Personal is now active. "
                f"You can manage your calendars at your "
                f'<a href="{account_url}">calendar dashboard</a>.'
            ),
            "If you have any questions, reply to this email.",
        ],
        User.SubscriptionTier.BUSINESS: [
            (
                f"Your upgrade to MergeCal Business is now active. "
                f"You can manage your calendars at your "
                f'<a href="{account_url}">calendar dashboard</a>.'
            ),
            "If you need assistance, reply to this email.",
        ],
        User.SubscriptionTier.SUPPORTER: [
            (
                f"Your MergeCal Supporter subscription is now active. "
                f"You can manage your calendars at your "
                f'<a href="{account_url}">calendar dashboard</a>.'
            ),
            (
                "If you'd like to join our Discord community, reply with "
                "your Discord username and I'll send you an invite."
            ),
        ],
    }

    body_list = bodies.get(tier, [])
    ps = "Thanks for your support!"

    return send_email(
        to_users=[user],
        subject=subject,
        bodies=body_list,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
    )


def downgrade_subscription_email(user: User) -> int:
    """Send subscription downgrade notification email."""
    subject = "Your MergeCal subscription has been updated"

    bodies = [
        "Your MergeCal subscription has been downgraded.",
        (
            "You can upgrade at any time from your account settings if you'd "
            "like to regain access to premium features."
        ),
    ]

    return send_email(
        to_users=[user],
        subject=subject,
        bodies=bodies,
        from_email="Abe <abe@mergecal.org>",
    )


def send_trial_ending_email(user: User) -> int:
    """Send trial ending reminder email."""
    subject = "Your MergeCal trial is ending soon"

    bodies = [
        "Your MergeCal trial will end in a few days.",
        "To continue using MergeCal, please add a payment method to your account.",
        "If you have questions, reply to this email.",
    ]

    ps = "If you need help with pricing, let me know and we can work something out."

    return send_email(
        to_users=[user],
        subject=subject,
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
    )
