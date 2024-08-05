# mergecal/core/constants.py
from mergecal.users.models import User

# Calendar limits for different subscription tiers
CALENDAR_LIMITS = {
    User.SubscriptionTier.PERSONAL: 2,
    User.SubscriptionTier.BUSINESS: 5,
}

SOURCE_LIMITS = {
    User.SubscriptionTier.PERSONAL: 3,
    User.SubscriptionTier.BUSINESS: 5,
}


# Mailjet template ids
class MailjetTemplates:
    FEEDBACK = "6172264"
    BASE = "6190328"