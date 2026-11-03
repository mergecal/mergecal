from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _

from mergecalweb.core import tiers
from mergecalweb.core.tiers import SubscriptionTier


class User(AbstractUser):
    """
    Default custom user model for MergeCal.
    If adding fields that need to be filled at user signup,
    check forms.SignupForm and forms.SocialSignupForms accordingly.
    """

    # First and last name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None  # type: ignore[assignment]
    last_name = None  # type: ignore[assignment]

    SubscriptionTier = SubscriptionTier

    subscription_tier = CharField(
        max_length=14,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.FREE,
    )

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})

    @property
    def is_free_tier(self) -> bool:
        """Check if user is on free tier."""
        return self.subscription_tier == self.SubscriptionTier.FREE

    @property
    def show_branding(self) -> bool:
        """Branding is shown unless the tier includes branding removal."""
        return not tiers.has_premium_features(self.subscription_tier)

    @cached_property
    def can_set_update_frequency(self) -> bool:
        return tiers.has_premium_features(self.subscription_tier)

    @cached_property
    def can_remove_branding(self) -> bool:
        return tiers.has_premium_features(self.subscription_tier)

    @cached_property
    def can_customize_sources(self) -> bool:
        return tiers.has_premium_features(self.subscription_tier)

    @property
    def can_add_calendar(self) -> bool:
        limit = tiers.calendar_limit(self.subscription_tier)
        return self.calendar_set.count() < limit
