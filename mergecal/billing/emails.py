# ruff: noqa: E501

import logging

from django.conf import settings
from django.urls import reverse

from mergecal.core.constants import MailjetTemplates
from mergecal.core.emails import MultiBodyTemplateEmailMessage
from mergecal.core.utils import get_site_url
from mergecal.users.models import User

logger = logging.getLogger(__name__)


def upgrade_subscription_email(
    user: User,
    new_tier: User.SubscriptionTier,
) -> MultiBodyTemplateEmailMessage:
    subject = f"Welcome to MergeCal {new_tier.label} Tier!"
    bodies = get_subscription_email_bodies(new_tier)
    ps = "If you have any questions, please don't hesitate to contact our support team."

    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email=settings.DEFAULT_FROM_EMAIL,
        template_id=MailjetTemplates.FOUR_PARAGRAPHS,
    )


def downgrade_subscription_email(user: User) -> MultiBodyTemplateEmailMessage:
    subject = "Your MergeCal Subscription Has Been Updated"
    bodies = [
        f"Dear {user.username},",
        "We want to inform you that your MergeCal subscription has been updated to the Free tier. We hope you've found value in the premium features you've experienced.",
        "You can still enjoy MergeCal's core features on the Free tier, including basic calendar merging capabilities.",
        "If you'd like to regain access to premium features, you can upgrade your subscription at any time from your account settings.",
    ]
    ps = "Thank you for being a MergeCal user. We appreciate your support!"

    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email=settings.DEFAULT_FROM_EMAIL,
        template_id=MailjetTemplates.FOUR_PARAGRAPHS,
    )


def get_subscription_email_bodies(tier: User.SubscriptionTier) -> list[str]:
    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")

    common_intro = (
        f"Welcome to the MergeCal {tier.label}! We're excited to have you on board."
    )

    bodies = {
        User.SubscriptionTier.PERSONAL: [
            common_intro,
            "With the Personal tier, you now have access to:",
            "• Updates every 12 hours to merged calendar feeds\n• Limit of 2 calendars\n• Limit of 3 feeds per calendar\n• MergeCal branding included",
            f"To start using your new features, head over to your account settings at {account_url}. If you need any assistance, our support team is here to help!",
        ],
        User.SubscriptionTier.BUSINESS: [
            common_intro,
            "The Business tier unlocks powerful features for professional calendar management:",
            "• Real-time updates to merged calendar feeds\n• Up to 5 calendars integration\n• Limit of 5 feeds per calendar\n• Option to remove MergeCal branding\n• Customizable event titles and descriptions",
            f"To configure your new features, please visit your account settings at {account_url}. Our team is ready to assist you in maximizing the benefits of your Business tier subscription.",
        ],
        User.SubscriptionTier.SUPPORTER: [
            common_intro,
            "As a Supporter, you now have access to our premium experience:",
            "• Unlimited Calendars and Calendar feeds\n• Real-time updates\n• MergeCal branding removal option\n• Embed Merged Calendar on your site (iFrame)\n• Influence on future development\n• Optional recognition on the MergeCal website\n• Access to exclusive Discord community",
            f"To explore your new features and benefits, check out your account settings at {account_url}. We're thrilled to have you as a Supporter and look forward to your input on MergeCal's future!",
        ],
    }

    return bodies.get(tier, [])
