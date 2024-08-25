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
            "Thank you for upgrading to MergeCal Personal. We're excited to have you with us.",
            f"Visit your Calendar Management page at {account_url} to set up your merged calendars and explore new capabilities.",
            "Our support team is available if you need assistance. We're committed to ensuring a smooth experience with MergeCal.",
        ],
        User.SubscriptionTier.BUSINESS: [
            "Welcome to MergeCal Business. We appreciate you choosing our service for your organization.",
            f"Access your enhanced Calendar Management page at {account_url}. Configure your expanded integrations and customize settings for your needs.",
            "Our team is ready to help you maximize these features and streamline your calendar management.",
        ],
        User.SubscriptionTier.SUPPORTER: [
            "Thank you for becoming a MergeCal Supporter. Your commitment helps drive our development.",
            f"Explore your new capabilities on the Calendar Management page at {account_url}, including unlimited calendars and embedding options.",
            "As a Supporter, we value your input. We welcome your suggestions for improvements.",
            "Contact us with your Discord username to join our community and receive early feature updates.",
        ],
    }
    return bodies.get(tier, []), ""


def get_subscription_email_ps(tier: User.SubscriptionTier) -> str:
    ps = {
        User.SubscriptionTier.PERSONAL: "We'd love to hear about your experience with MergeCal. Feel free to share your thoughts.",
        User.SubscriptionTier.BUSINESS: "We'd be interested in learning how MergeCal benefits your organization. Your feedback is valuable to us.",
        User.SubscriptionTier.SUPPORTER: "Your insights as a Supporter are crucial. We'd appreciate hearing about your experience with MergeCal.",
    }
    return ps.get(tier, "")


def send_trial_ending_email(user: User) -> MultiBodyTemplateEmailMessage:
    subject = "Your MergeCal Trial is Ending Soon"
    bodies = [
        "This is a friendly reminder that your MergeCal trial is ending in a few days. To continue using MergeCal, please add a payment method to your account before your trial expires.",
        "We hope MergeCal has been helpful in simplifying your calendar management. By subscribing, you'll ensure uninterrupted access to the service you've been using during your trial period.",
        "If you have any questions about subscribing or need assistance with your account, please don't hesitate to reply to this email or contact our support team. We're here to help!",
    ]

    ps = "P.S. If money is tight and you'd like to continue using MergeCal, please reply to this email. We're happy to offer you a discount to help you stay connected and productive."

    return MultiBodyTemplateEmailMessage(
        subject=subject,
        to_users=[user],
        bodies=bodies,
        ps=ps,
        from_email="Abe <abe@mergecal.org>",
        template_id=MailjetTemplates.THREE_PARAGRAPHS,
    )
