# ruff: noqa: E501

import logging

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
    subject = f"Welcome to MergeCal {new_tier.label}!"
    bodies = get_subscription_email_bodies(new_tier)
    ps = "P.S. If you have any questions, please don't hesitate to contact our support team."
    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.com>",
        template_id=MailjetTemplates.FOUR_PARAGRAPHS,
    )


def downgrade_subscription_email(user: User) -> MultiBodyTemplateEmailMessage:
    subject = "Your MergeCal Subscription Has Been Updated"
    bodies = [
        f"Dear {user.username},",
        "I wanted to personally inform you that your MergeCal subscription has been updated to the Free tier. I hope you've found value in the premium features you've experienced.",
        "You can still enjoy MergeCal's core features on the Free tier, including basic calendar merging capabilities.",
        "If you'd like to regain access to premium features, you can upgrade your subscription at any time from your account settings.",
    ]
    ps = "Thank you for being a MergeCal user. I truly appreciate your support!"
    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
        template_id=MailjetTemplates.FOUR_PARAGRAPHS,
    )


def get_subscription_email_bodies(tier: User.SubscriptionTier) -> list[str]:
    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")
    common_intro = f"Welcome to the MergeCal {tier.label}! I'm Abe, the creator of MergeCal, and I'm thrilled to have you on board."
    bodies = {
        User.SubscriptionTier.PERSONAL: [
            common_intro,
            "With the Personal tier, you now have access to:",
            "• Updates every 12 hours to merged calendar feeds  • Limit of 2 calendars  • Limit of 3 feeds per calendar  • MergeCal branding included",
            f"To start using your new features, head over to your calendar management page at {account_url}. If you need any assistance, our support team and I are here to help!",
        ],
        User.SubscriptionTier.BUSINESS: [
            common_intro,
            "The Business tier unlocks powerful features for professional calendar management:",
            "• Real-time updates to merged calendar feeds  • Up to 5 calendars integration  • Limit of 5 feeds per calendar  • Option to remove MergeCal branding  • Customizable event titles and descriptions",
            f"To configure your new features, please visit your calendar management page at {account_url}. Our team and I are ready to assist you in maximizing the benefits of your Business tier subscription.",
        ],
        User.SubscriptionTier.SUPPORTER: [
            common_intro,
            "As a Supporter, you now have access to our premium experience:",
            "• Unlimited Calendars and Calendar feeds  • Real-time updates  • MergeCal branding removal option  • Embed Merged Calendar on your site (iFrame)  • Influence on future development  • Optional recognition on the MergeCal website  • Access to exclusive Discord community",
            f"To explore your new features and benefits, check out your calendar management page at {account_url}. I'm personally thrilled to have you as a Supporter and look forward to your input on MergeCal's future!",
        ],
    }
    return bodies.get(tier, [])
