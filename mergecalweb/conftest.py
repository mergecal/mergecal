from collections.abc import Iterator
from pathlib import Path
from unittest.mock import MagicMock
from unittest.mock import patch

import pytest
import responses
from django.core.cache import cache
from django.http import HttpRequest
from django.test import Client

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory


@pytest.fixture
def test_calendars_dir() -> Path:
    """Get the directory containing test calendar files."""
    return Path(__file__).parent / "calendars" / "tests" / "calendars"


@pytest.fixture
def http() -> Iterator[responses.RequestsMock]:
    """Fake HTTP server for `requests`; each registered URL must be fetched."""
    with responses.RequestsMock() as rsps:
        yield rsps


@pytest.fixture
def mock_calendar_request(test_calendars_dir: Path) -> Iterator[None]:
    """Serve each test calendar file at http://example.com/<filename>."""
    with responses.RequestsMock(assert_all_requests_are_fired=False) as rsps:
        for path in test_calendars_dir.glob("*.ics"):
            rsps.get(
                f"http://example.com/{path.name}",
                body=path.read_bytes(),
                content_type="text/calendar",
            )
        yield


@pytest.fixture(autouse=True)
def _clear_cache() -> None:
    cache.clear()


@pytest.fixture
def mock_request() -> HttpRequest:
    """Create a mock HTTP request."""
    request = HttpRequest()
    request.user = UserFactory()
    return request


@pytest.fixture
def business_user() -> User:
    """Create a test user with business tier access."""
    return UserFactory(subscription_tier=User.SubscriptionTier.BUSINESS)


@pytest.fixture
def supporter_user() -> User:
    """Create a test user with supporter tier access."""
    return UserFactory(subscription_tier=User.SubscriptionTier.SUPPORTER)


@pytest.fixture
def calendar(business_user: User) -> Calendar:
    """Create a test calendar for the business user."""
    return CalendarFactory(owner=business_user)


@pytest.fixture
def source(calendar: Calendar) -> Source:
    return SourceFactory(calendar=calendar)


@pytest.fixture
def authenticated_client(business_user: User) -> Client:
    """Create an authenticated test client."""
    client = Client()
    client.force_login(business_user)
    return client


@pytest.fixture(autouse=True)
def _media_storage(settings, tmpdir) -> None:
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user(db) -> User:
    return UserFactory()


@pytest.fixture(scope="session", autouse=True)
def patch_price_get():
    with patch(
        "djstripe.models.core.Price.objects.get",
        return_value=MagicMock(id="price_123", lookup_key="personal_monthly"),
    ) as mock_method:
        yield mock_method


@pytest.fixture(scope="session", autouse=True)
def patch_customer_get_or_create():
    with patch(
        "djstripe.models.Customer.get_or_create",
        return_value=(MagicMock(), True),
    ) as mock_method:
        yield mock_method


@pytest.fixture(scope="session", autouse=True)
def patch_coupon_get():
    with patch(
        "djstripe.models.billing.Coupon.objects.get",
        return_value=MagicMock(name="beta tester", id="coupon_123"),
    ) as mock_method:
        yield mock_method


@pytest.fixture(scope="session", autouse=True)
def path_subscription_create():
    with patch(
        "stripe.Subscription.create",
        return_value=MagicMock(id="sub_123"),
    ) as mock_method:
        yield mock_method
