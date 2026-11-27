from uuid import uuid4

import pytest
from django.contrib.sites.models import Site

from mergecalweb.calendars.forms import CalendarForm
from mergecalweb.calendars.forms import SourceForm
from mergecalweb.calendars.models import TWELVE_HOURS_IN_SECONDS
from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db

FEED_URL = "https://feeds.example.org/basic.ics"
Tier = User.SubscriptionTier
LOCKED_TIERS = [Tier.FREE, Tier.PERSONAL]
PREMIUM_TIERS = [Tier.BUSINESS, Tier.SUPPORTER]
PREMIUM_SOURCE_FIELDS = [
    "include_title",
    "include_description",
    "include_location",
    "custom_prefix",
    "exclude_keywords",
]


def calendar_data(**overrides):
    return {
        "name": "Team schedule",
        "timezone": "America/New_York",
        "update_frequency_seconds": TWELVE_HOURS_IN_SECONDS,
        **overrides,
    }


def source_data(**overrides):
    return {
        "name": "Practice",
        "url": FEED_URL,
        "include_title": True,
        "include_description": True,
        "include_location": True,
        **overrides,
    }


@pytest.fixture
def feed(http, test_calendars_dir):
    http.get(FEED_URL, body=(test_calendars_dir / "basic.ics").read_bytes())


class TestCalendarForm:
    @pytest.mark.parametrize("tier", LOCKED_TIERS)
    def test_premium_fields_are_disabled_for_lower_tiers(self, tier):
        form = CalendarForm(user=UserFactory(subscription_tier=tier))

        assert form.fields["update_frequency_seconds"].disabled
        assert form.fields["remove_branding"].disabled

    @pytest.mark.parametrize("tier", PREMIUM_TIERS)
    def test_premium_fields_are_enabled_for_paid_tiers(self, tier):
        form = CalendarForm(user=UserFactory(subscription_tier=tier))

        assert not form.fields["update_frequency_seconds"].disabled
        assert not form.fields["remove_branding"].disabled

    def test_personal_user_cannot_post_premium_values(self):
        user = UserFactory(subscription_tier=Tier.PERSONAL)
        form = CalendarForm(
            data=calendar_data(update_frequency_seconds=60, remove_branding="on"),
            user=user,
        )

        assert form.is_valid(), form.errors
        calendar = form.save()
        assert calendar.update_frequency_seconds == TWELVE_HOURS_IN_SECONDS
        assert calendar.remove_branding is False

    def test_personal_user_cannot_change_premium_values_on_edit(self):
        user = UserFactory(subscription_tier=Tier.PERSONAL)
        calendar = CalendarFactory(owner=user)
        form = CalendarForm(
            data=calendar_data(update_frequency_seconds=60, remove_branding="on"),
            instance=calendar,
            user=user,
        )

        assert form.is_valid(), form.errors
        form.save()
        calendar.refresh_from_db()
        assert calendar.update_frequency_seconds == TWELVE_HOURS_IN_SECONDS
        assert calendar.remove_branding is False

    @pytest.mark.parametrize("tier", PREMIUM_TIERS)
    def test_paid_user_can_set_premium_values(self, tier):
        user = UserFactory(subscription_tier=tier)
        form = CalendarForm(
            data=calendar_data(update_frequency_seconds=3600, remove_branding="on"),
            user=user,
        )

        assert form.is_valid(), form.errors
        calendar = form.save()
        assert calendar.owner == user
        assert calendar.update_frequency_seconds == 3600  # noqa: PLR2004
        assert calendar.remove_branding is True

    def test_free_user_cannot_create_a_calendar(self):
        form = CalendarForm(data=calendar_data(), user=UserFactory())

        assert not form.is_valid()
        assert form.non_field_errors() == ["Upgrade to create more calendars."]

    def test_personal_user_at_calendar_limit_cannot_create_another(self):
        user = UserFactory(subscription_tier=Tier.PERSONAL)
        CalendarFactory.create_batch(2, owner=user)
        form = CalendarForm(data=calendar_data(), user=user)

        assert not form.is_valid()
        assert form.non_field_errors() == ["Upgrade to create more calendars."]

    def test_user_at_calendar_limit_can_still_edit_a_calendar(self):
        user = UserFactory(subscription_tier=Tier.PERSONAL)
        calendar, _ = CalendarFactory.create_batch(2, owner=user)
        form = CalendarForm(
            data=calendar_data(name="Renamed"),
            instance=calendar,
            user=user,
        )

        assert form.is_valid(), form.errors
        form.save()
        calendar.refresh_from_db()
        assert calendar.name == "Renamed"

    def test_name_and_timezone_are_validated(self, business_user):
        form = CalendarForm(
            data=calendar_data(name="", timezone="Mars/Olympus_Mons"),
            user=business_user,
        )

        assert not form.is_valid()
        assert set(form.errors) == {"name", "timezone"}


class TestSourceForm:
    def test_valid_feed_is_saved_to_the_calendar(self, calendar, feed):
        form = SourceForm(data=source_data(), calendar=calendar)

        assert form.is_valid(), form.errors
        source = form.save()
        assert source.calendar == calendar
        assert source.url == FEED_URL

    @pytest.mark.parametrize("tier", LOCKED_TIERS)
    def test_customization_fields_are_disabled_for_lower_tiers(self, tier):
        calendar = CalendarFactory(owner=UserFactory(subscription_tier=tier))
        form = SourceForm(calendar=calendar)

        for field in PREMIUM_SOURCE_FIELDS:
            assert form.fields[field].disabled
            assert (
                form.fields[field].help_text
                == "Available on Business and Supporter plans"
            )

    @pytest.mark.parametrize("tier", PREMIUM_TIERS)
    def test_customization_fields_are_enabled_for_paid_tiers(self, tier):
        calendar = CalendarFactory(owner=UserFactory(subscription_tier=tier))
        form = SourceForm(calendar=calendar)

        for field in PREMIUM_SOURCE_FIELDS:
            assert not form.fields[field].disabled

    def test_personal_user_cannot_post_customizations(self, feed):
        user = UserFactory(subscription_tier=Tier.PERSONAL)
        calendar = CalendarFactory(owner=user)
        form = SourceForm(
            data=source_data(
                include_title="",
                include_description="",
                include_location="",
                custom_prefix="[Work]",
                exclude_keywords="cancelled",
            ),
            calendar=calendar,
        )

        assert form.is_valid(), form.errors
        source = form.save()
        assert source.include_title is True
        assert source.include_description is True
        assert source.include_location is True
        assert source.custom_prefix == ""
        assert source.exclude_keywords == ""

    def test_business_user_can_post_customizations(self, calendar, feed):
        form = SourceForm(
            data=source_data(
                include_title="",
                custom_prefix="[Work]",
                exclude_keywords="cancelled",
            ),
            calendar=calendar,
        )

        assert form.is_valid(), form.errors
        source = form.save()
        assert source.include_title is False
        assert source.custom_prefix == "[Work]"
        assert source.exclude_keywords == "cancelled"

    def test_calendar_at_source_limit_rejects_a_new_source(self, calendar):
        SourceFactory.create_batch(5, calendar=calendar)
        form = SourceForm(
            data=source_data(url="https://www.meetup.com/some-group/events/ical/"),
            calendar=calendar,
        )

        assert not form.is_valid()
        assert form.non_field_errors() == ["upgrade to add more sources"]

    def test_calendar_at_source_limit_can_still_edit_a_source(self, calendar):
        source, *_ = SourceFactory.create_batch(5, calendar=calendar)
        meetup_url = "https://www.meetup.com/some-group/events/ical/"
        form = SourceForm(
            data=source_data(name="Renamed", url=meetup_url),
            instance=source,
            calendar=calendar,
        )

        assert form.is_valid(), form.errors

    def test_html_page_is_rejected(self, calendar, http):
        http.get(FEED_URL, body="<!DOCTYPE html><html></html>")
        form = SourceForm(data=source_data(), calendar=calendar)

        assert not form.is_valid()
        assert "HTML page instead of an iCalendar feed" in form.errors["url"][0]

    def test_unreachable_feed_is_rejected(self, calendar, http):
        http.get(FEED_URL, status=404)
        form = SourceForm(data=source_data(), calendar=calendar)

        assert not form.is_valid()
        assert "url" in form.errors

    def test_malformed_url_is_rejected_without_fetching(self, calendar, http):
        form = SourceForm(data=source_data(url="not a url"), calendar=calendar)

        assert not form.is_valid()
        assert form.errors["url"] == ["Enter a valid URL."]

    def test_meetup_url_is_accepted_without_fetching(self, calendar, http):
        meetup_url = "https://www.meetup.com/some-group/events/ical/"
        form = SourceForm(data=source_data(url=meetup_url), calendar=calendar)

        assert form.is_valid(), form.errors

    def test_existing_mergecal_calendar_is_accepted_without_fetching(
        self,
        calendar,
        http,
    ):
        other = CalendarFactory()
        url = f"https://{Site.objects.get_current().domain}{other.get_calendar_file_url()}"
        form = SourceForm(data=source_data(url=url), calendar=calendar)

        assert form.is_valid(), form.errors

    def test_missing_mergecal_calendar_is_rejected(self, calendar, http):
        domain = Site.objects.get_current().domain
        url = f"https://{domain}/calendars/{uuid4()}.ics"
        form = SourceForm(data=source_data(url=url), calendar=calendar)

        assert not form.is_valid()
        assert form.errors["url"] == [
            "The specified MergeCal calendar does not exist.",
        ]
