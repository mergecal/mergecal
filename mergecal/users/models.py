from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.db.models import TextChoices
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


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

    class SubscriptionTier(TextChoices):
        NONE = "none", "None"
        BASIC = "basic", "Basic"
        PREMIUM = "premium", "Premium"
        ELITE = "elite", "Elite"

    subscription_tier = CharField(
        max_length=10,
        choices=SubscriptionTier.choices,
        default=SubscriptionTier.NONE,
    )

    def get_absolute_url(self) -> str:
        """Get URL for user's detail view.

        Returns:
            str: URL for user detail.

        """
        return reverse("users:detail", kwargs={"username": self.username})
