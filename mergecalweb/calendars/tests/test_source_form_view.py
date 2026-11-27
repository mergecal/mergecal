import pytest
from django.urls import reverse

from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

UPSELL = "Premium Features"


def add_source_page(client, tier):
    owner = UserFactory()
    client.force_login(owner)
    owner.subscription_tier = tier
    owner.save()
    calendar = CalendarFactory(owner=owner)
    url = reverse("calendars:source_add", kwargs={"uuid": calendar.uuid})
    return client.get(url).content.decode()


@pytest.mark.django_db
@pytest.mark.parametrize(
    "tier",
    [User.SubscriptionTier.BUSINESS, User.SubscriptionTier.SUPPORTER],
)
def test_add_source_skips_upsell_for_paid_tiers(client, tier):
    assert UPSELL not in add_source_page(client, tier)


@pytest.mark.django_db
def test_add_source_shows_upsell_to_personal_tier(client):
    assert UPSELL in add_source_page(client, User.SubscriptionTier.PERSONAL)
