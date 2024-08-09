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
    ps = get_subscription_email_ps(new_tier)
    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
        template_id=MailjetTemplates.FOUR_PARAGRAPHS,
    )


def downgrade_subscription_email(user: User) -> MultiBodyTemplateEmailMessage:
    subject = "Your MergeCal Subscription Has Been Updated"
    bodies = [
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


def get_subscription_email_bodies(tier: User.SubscriptionTier) -> tuple[list[str], str]:
    base_url = get_site_url()
    account_url = base_url + reverse("calendars:calendar_list")

    bodies = {
        User.SubscriptionTier.PERSONAL: [
            "Thank you for upgrading to MergeCal Personal. We're excited to have you on board and can't wait for you to experience the enhanced features of your new plan.",
            f"To get started, please visit your Calendar Management page at {account_url}. Here you can set up your merged calendars and explore the new capabilities at your disposal.",
            "If you have any questions or need assistance, our support team is here to help. We're committed to making your experience with MergeCal as smooth and productive as possible.",
        ],
        User.SubscriptionTier.BUSINESS: [
            "Welcome to MergeCal Business. We're thrilled that you've chosen our service for your business needs and we're committed to helping you make the most of it.",
            f"To leverage your new subscription, visit your enhanced Calendar Management page at {account_url}. Here you can configure your expanded calendar integrations and customize settings to suit your business requirements.",
            "Our support team is ready to assist you in maximizing these features. We're dedicated to helping your business streamline its calendar management and boost productivity.",
        ],
        User.SubscriptionTier.SUPPORTER: [
            "Thank you for becoming a MergeCal Supporter. Your commitment is invaluable in driving our development and improving MergeCal for everyone.",
            f"To start exploring your new capabilities, visit your Calendar Management page at {account_url}. You'll find a host of advanced features there, including unlimited calendars and embedding options.",
            "As a Supporter, your input is especially valuable to us. We welcome your suggestions for new features or improvements. Your support truly makes a difference in shaping the future of MergeCal.",
            "Reply with your Discord username to join our exclusive community. Connect with power users and get early feature insights.",
        ],
    }
    return bodies.get(tier, ([], ""))


def get_subscription_email_ps(tier: User.SubscriptionTier) -> str:
    ps = {
        User.SubscriptionTier.PERSONAL: "P.S. If you're open to sharing how you use MergeCal, we'd be interested in featuring your story. Reply to this email if you'd like to participate.",
        User.SubscriptionTier.BUSINESS: "P.S. If you're open to sharing how you use MergeCal, we'd be interested in featuring your story. Reply to this email if you'd like to participate.",
        User.SubscriptionTier.SUPPORTER: "P.S. If you're open to sharing how you use MergeCal, we'd be interested in featuring your story. Reply to this email if you'd like to participate.",
    }
    return ps.get(tier, "")
