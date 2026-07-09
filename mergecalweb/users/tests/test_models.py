import pytest

from mergecalweb.calendars.models import Calendar
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory


def test_user_get_absolute_url(user: User):
    assert user.get_absolute_url() == f"/users/{user.username}/"


@pytest.mark.django_db
class TestTierEntitlements:
    """Characterization tests pinning subscription-tier entitlement behavior.

    The tier rules are being consolidated into a single module; these tests
    document the current behavior so the refactor provably preserves it.
    """

    @pytest.mark.parametrize(
        ("tier", "premium"),
        [
            (User.SubscriptionTier.FREE, False),
            (User.SubscriptionTier.PERSONAL, False),
            (User.SubscriptionTier.BUSINESS, True),
            (User.SubscriptionTier.SUPPORTER, True),
            ("legacy_tier", False),
        ],
    )
    def test_premium_feature_flags(self, tier: str, *, premium: bool) -> None:
        user = UserFactory(subscription_tier=tier)
        assert user.can_set_update_frequency is premium
        assert user.can_remove_branding is premium
        assert user.can_customize_sources is premium
        assert user.show_branding is (not premium)

    @pytest.mark.parametrize(
        ("tier", "limit"),
        [
            (User.SubscriptionTier.FREE, 0),
            (User.SubscriptionTier.PERSONAL, 2),
            (User.SubscriptionTier.BUSINESS, 5),
        ],
    )
    def test_can_add_calendar_enforces_tier_limit(self, tier: str, limit: int) -> None:
        user = UserFactory(subscription_tier=tier)
        for i in range(limit):
            assert user.can_add_calendar
            Calendar.objects.create(name=f"Calendar {i + 1}", owner=user)
        assert not user.can_add_calendar

    def test_supporter_calendar_count_is_unlimited(self) -> None:
        user = UserFactory(subscription_tier=User.SubscriptionTier.SUPPORTER)
        for i in range(6):  # one past the largest finite tier limit
            Calendar.objects.create(name=f"Calendar {i + 1}", owner=user)
        assert user.can_add_calendar

    def test_unknown_tier_cannot_add_calendar(self) -> None:
        user = UserFactory(subscription_tier="legacy_tier")
        assert not user.can_add_calendar
