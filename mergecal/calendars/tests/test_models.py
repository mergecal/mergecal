# ruff: noqa: FBT001
import uuid
from unittest.mock import patch

import pytest
from django.contrib.sites.models import Site
from django.core.exceptions import ValidationError

from mergecal.calendars.models import Calendar
from mergecal.calendars.models import Source
from mergecal.users.models import User

TWELVE_HOURS_IN_SECONDS = 43200


@pytest.mark.django_db
class TestCalendarModel:
    """Test suite for Calendar model functionality."""

    def test_calendar_creation_basic(self, business_user: User) -> None:
        """Test basic calendar creation with required fields."""
        calendar = Calendar.objects.create(
            name="Test Calendar",
            owner=business_user,
            timezone="UTC",
        )
        assert calendar.name == "Test Calendar"
        assert isinstance(calendar.uuid, uuid.UUID)
        assert calendar.update_frequency_seconds == TWELVE_HOURS_IN_SECONDS
        assert not calendar.remove_branding
        assert str(calendar) == "Test Calendar"

        # Test URL methods
        assert calendar.get_calendar_file_url() == f"/calendars/{calendar.uuid}.ical"
        assert (
            calendar.get_calendar_view_url() == f"/calendars/{calendar.uuid}/calendar/"
        )

        # Test iframe - don't test full URL, just path
        iframe = calendar.get_calendar_iframe()
        assert f"/calendars/iframe/{calendar.uuid}/" in iframe
        assert 'width="100%"' in iframe
        assert 'height="600"' in iframe

    @pytest.mark.parametrize(
        "timezone",
        ["America/New_York", "Europe/London", "Asia/Tokyo", "UTC", "Australia/Sydney"],
    )
    def test_calendar_timezone_validation(
        self,
        business_user: User,
        timezone: str,
    ) -> None:
        """Test calendar creation with various valid timezones."""
        calendar = Calendar(
            name="Timezone Test",
            owner=business_user,
            timezone=timezone,
        )
        calendar.full_clean()  # Validate but don't save
        calendar.save()
        assert calendar.timezone == timezone

    def test_calendar_invalid_timezone(self, business_user: User) -> None:
        """Test calendar creation with invalid timezone."""
        calendar = Calendar(
            name="Invalid Timezone",
            owner=business_user,
            timezone="Invalid/Zone",
        )
        with pytest.raises(ValidationError):
            calendar.full_clean()

    @pytest.mark.parametrize(
        ("tier", "limit"),
        [
            (User.SubscriptionTier.FREE, 1),
            (User.SubscriptionTier.PERSONAL, 2),
            (User.SubscriptionTier.BUSINESS, 5),
        ],
    )
    def test_calendar_limits_by_tier(self, tier: str, limit: int) -> None:
        """Test calendar creation limits for different subscription tiers."""
        unique_id = str(uuid.uuid4())[:8]
        user = User.objects.create(
            username=f"test_user_{unique_id}",
            email=f"test_{unique_id}@example.com",
            subscription_tier=tier,
        )

        # Create calendars up to the limit
        calendars = []
        for i in range(limit):
            calendar = Calendar.objects.create(
                name=f"Calendar {i+1}",
                owner=user,
            )
            calendars.append(calendar)

        # Attempting to create one more should fail
        extra_calendar = Calendar(
            name="Extra Calendar",
            owner=user,
        )
        with pytest.raises(ValidationError) as exc:
            extra_calendar.full_clean()
        assert "Upgrade to create more calendars" in str(exc.value)

    def test_calendar_update_frequency_permissions(self) -> None:
        """Test update frequency restrictions based on subscription tier."""
        free_id = str(uuid.uuid4())[:8]
        business_id = str(uuid.uuid4())[:8]

        # Create users with unique usernames and emails
        free_user = User.objects.create(
            username=f"free_user_{free_id}",
            email=f"free_{free_id}@example.com",
            subscription_tier=User.SubscriptionTier.FREE,
        )
        business_user = User.objects.create(
            username=f"business_user_{business_id}",
            email=f"business_{business_id}@example.com",
            subscription_tier=User.SubscriptionTier.BUSINESS,
        )

        # Free user cannot set custom frequency
        cal_free = Calendar(
            name="Free Calendar",
            owner=free_user,
            update_frequency_seconds=300,  # Try to set 5 minutes
        )
        with pytest.raises(ValidationError):
            cal_free.full_clean()

        # Business user can set custom frequency
        new_value = 300  # 5 minutes
        cal_business = Calendar(
            name="Business Calendar",
            owner=business_user,
            update_frequency_seconds=new_value,
        )
        cal_business.full_clean()
        cal_business.save()
        assert cal_business.effective_update_frequency == new_value


@pytest.mark.django_db
class TestSourceModel:
    def test_source_creation_basic(self, calendar: Calendar) -> None:
        """Test basic source creation with default values."""
        with patch("mergecal.calendars.models.CalendarFetcher") as mock_fetcher:
            mock_instance = mock_fetcher.return_value
            mock_instance.fetch_calendar.return_value = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

            source = Source(
                name="Test Source",
                url="https://example.com/feed.ics",
                calendar=calendar,
            )
            source.full_clean()
            source.save()

            assert source.name == "Test Source"
            assert source.include_title is True
            assert source.include_description is True
            assert source.include_location is True
            assert source.custom_prefix == ""
            assert source.exclude_keywords == ""

    def test_source_url_validation(self, calendar: Calendar) -> None:
        """Test URL validation for different types of URLs."""
        site = Site.objects.get_current()

        # Test valid Meetup URL
        meetup_source = Source(
            name="Meetup Source",
            url="https://www.meetup.com/group/events.ics",
            calendar=calendar,
        )
        meetup_source.full_clean()

        # Test valid local calendar URL
        local_cal = Calendar.objects.create(name="Local Calendar", owner=calendar.owner)
        local_url = f"https://{site.domain}/calendars/{local_cal.uuid}.ical"
        local_source = Source(
            name="Local Source",
            url=local_url,
            calendar=calendar,
        )
        local_source.full_clean()

        # Test valid external URL
        with patch("mergecal.calendars.models.CalendarFetcher") as mock_fetcher:
            mock_instance = mock_fetcher.return_value
            mock_instance.fetch_calendar.return_value = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

            external_source = Source(
                name="External Source",
                url="https://example.com/feed.ics",
                calendar=calendar,
            )
            external_source.full_clean()

    def test_source_invalid_urls(self, calendar: Calendar) -> None:
        """Test validation fails for invalid URLs."""
        with patch("mergecal.calendars.models.CalendarFetcher") as mock_fetcher:
            mock_instance = mock_fetcher.return_value
            mock_instance.fetch_calendar.side_effect = ValueError("Invalid iCal")

            source = Source(
                name="Invalid Source",
                url="https://example.com/not-ical.ics",
                calendar=calendar,
            )
            with pytest.raises(ValidationError):
                source.full_clean()

    def test_source_customization_permissions(self) -> None:
        """Test source customization based on subscription tier."""
        # Create users and calendars
        free_user = User.objects.create(
            username="free_user",
            email="free@example.com",
            subscription_tier=User.SubscriptionTier.FREE,
        )
        business_user = User.objects.create(
            username="business_user",
            email="business@example.com",
            subscription_tier=User.SubscriptionTier.BUSINESS,
        )

        free_cal = Calendar.objects.create(name="Free Calendar", owner=free_user)
        business_cal = Calendar.objects.create(
            name="Business Calendar",
            owner=business_user,
        )

        with patch("mergecal.calendars.models.CalendarFetcher") as mock_fetcher:
            mock_instance = mock_fetcher.return_value
            mock_instance.fetch_calendar.return_value = """BEGIN:VCALENDAR
VERSION:2.0
END:VCALENDAR"""

            # Free tier cannot customize sources
            free_source = Source(
                name="Free Source",
                url="https://example.com/feed.ics",
                calendar=free_cal,
                include_title=False,
                custom_prefix="[Test]",
            )
            with pytest.raises(ValidationError):
                free_source.full_clean()

            # Business tier can customize sources
            business_source = Source(
                name="Business Source",
                url="https://example.com/feed.ics",
                calendar=business_cal,
                include_title=False,
                include_description=False,
                include_location=False,
                custom_prefix="[Test]",
                exclude_keywords="keyword1,keyword2",
            )
            business_source.full_clean()
            business_source.save()

            assert not business_source.include_title
            assert not business_source.include_description
            assert business_source.custom_prefix == "[Test]"
