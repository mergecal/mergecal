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
