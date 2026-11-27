from __future__ import annotations

from http import HTTPStatus
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest
from django.core.cache import cache
from django.urls import reverse

from mergecalweb.calendars.cache import calendar_output_cache_key
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

from .factories import CalendarFactory
from .factories import SourceFactory

if TYPE_CHECKING:
    from pathlib import Path

    import responses
    from django.test import Client

pytestmark = pytest.mark.django_db

FEED_URL = "https://feeds.example.test/basic.ics"


def login(client: Client, user: User, tier: str) -> None:
    client.force_login(user)
    user.subscription_tier = tier
    user.save(update_fields=["subscription_tier"])


def serve_feed(http: responses.RequestsMock, test_calendars_dir: Path) -> None:
    http.get(
        FEED_URL,
        body=(test_calendars_dir / "basic.ics").read_bytes(),
        content_type="text/calendar",
    )


def calendar_data(name: str = "Team") -> dict[str, str]:
    return {
        "name": name,
        "timezone": "America/New_York",
        "update_frequency_seconds": "43200",
    }


def source_data(name: str = "Work") -> dict[str, str]:
    return {
        "name": name,
        "url": FEED_URL,
        "include_title": "on",
        "include_description": "on",
        "include_location": "on",
    }


class TestCalendarCreate:
    def test_anonymous_user_is_sent_to_login(self, client: Client) -> None:
        response = client.post(reverse("calendars:calendar_create"), calendar_data())

        assert response.status_code == HTTPStatus.FOUND
        assert response.url.startswith(reverse("account_login"))
        assert not Calendar.objects.exists()

    def test_creates_calendar_and_redirects_to_its_page(self, client: Client) -> None:
        user = UserFactory()
        login(client, user, User.SubscriptionTier.BUSINESS)

        response = client.post(reverse("calendars:calendar_create"), calendar_data())

        calendar = Calendar.objects.get(owner=user)
        assert calendar.name == "Team"
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(
            "calendars:calendar_update",
            kwargs={"uuid": calendar.uuid},
        )

    def test_personal_user_at_calendar_limit_cannot_create(
        self,
        client: Client,
    ) -> None:
        user = UserFactory()
        login(client, user, User.SubscriptionTier.PERSONAL)
        CalendarFactory.create_batch(2, owner=user)

        response = client.post(reverse("calendars:calendar_create"), calendar_data())

        assert response.status_code == HTTPStatus.OK
        assert "Upgrade to create more calendars." in response.content.decode()
        assert user.calendar_set.count() == 2  # noqa: PLR2004

    def test_free_user_cannot_create(self, client: Client) -> None:
        user = UserFactory()
        login(client, user, User.SubscriptionTier.FREE)

        response = client.post(reverse("calendars:calendar_create"), calendar_data())

        assert response.status_code == HTTPStatus.OK
        assert not user.calendar_set.exists()

    @pytest.mark.parametrize(
        ("detected", "expected"),
        [
            ("Europe/London", "Europe/London"),
            (-300, "America/New_York"),
        ],
    )
    def test_timezone_defaults_to_the_browsers_zone(
        self,
        client: Client,
        detected: str | int,
        expected: str,
    ) -> None:
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)
        session = client.session
        session["detected_tz"] = detected
        session.save()

        response = client.get(reverse("calendars:calendar_create"))

        assert response.context["form"]["timezone"].value() == expected


class TestCalendarUpdate:
    def test_owner_renames_calendar(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.BUSINESS)
        url = reverse("calendars:calendar_update", kwargs={"uuid": calendar.uuid})

        response = client.post(url, calendar_data(name="Renamed"))

        calendar.refresh_from_db()
        assert calendar.name == "Renamed"
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == url

    def test_other_user_gets_404(self, client: Client) -> None:
        calendar = CalendarFactory(name="Original")
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)
        url = reverse("calendars:calendar_update", kwargs={"uuid": calendar.uuid})

        assert client.get(url).status_code == HTTPStatus.NOT_FOUND
        assert client.post(url, calendar_data()).status_code == HTTPStatus.NOT_FOUND
        calendar.refresh_from_db()
        assert calendar.name == "Original"


class TestCalendarDelete:
    def test_owner_deletes_calendar(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:calendar_delete", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse("calendars:calendar_list")
        assert not Calendar.objects.filter(pk=calendar.pk).exists()

    def test_other_user_gets_404(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:calendar_delete", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Calendar.objects.filter(pk=calendar.pk).exists()


class TestSourceAdd:
    def test_owner_adds_source(
        self,
        client: Client,
        http: responses.RequestsMock,
        test_calendars_dir: Path,
    ) -> None:
        serve_feed(http, test_calendars_dir)
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:source_add", kwargs={"uuid": calendar.uuid}),
            source_data(),
        )

        source = Source.objects.get(calendar=calendar)
        assert source.url == FEED_URL
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(
            "calendars:calendar_update",
            kwargs={"uuid": calendar.uuid},
        )

    def test_other_user_gets_404(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:source_add", kwargs={"uuid": calendar.uuid}),
            source_data(),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert not Source.objects.exists()

    def test_personal_user_at_source_limit_cannot_add(
        self,
        client: Client,
        http: responses.RequestsMock,
        test_calendars_dir: Path,
    ) -> None:
        serve_feed(http, test_calendars_dir)
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.PERSONAL)
        SourceFactory.create_batch(3, calendar=calendar)

        response = client.post(
            reverse("calendars:source_add", kwargs={"uuid": calendar.uuid}),
            source_data(),
        )

        assert response.status_code == HTTPStatus.OK
        assert "upgrade to add more sources" in response.content.decode()
        assert calendar.calendarOf.count() == 3  # noqa: PLR2004


class TestSourceEdit:
    def test_owner_renames_source(
        self,
        client: Client,
        http: responses.RequestsMock,
        test_calendars_dir: Path,
    ) -> None:
        serve_feed(http, test_calendars_dir)
        source = SourceFactory(url=FEED_URL)
        login(client, source.calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:source_edit", kwargs={"pk": source.pk}),
            source_data(name="Renamed"),
        )

        source.refresh_from_db()
        assert source.name == "Renamed"
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(
            "calendars:calendar_update",
            kwargs={"uuid": source.calendar.uuid},
        )

    def test_other_user_gets_403(self, client: Client) -> None:
        source = SourceFactory(name="Original")
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)
        url = reverse("calendars:source_edit", kwargs={"pk": source.pk})

        assert client.get(url).status_code == HTTPStatus.FORBIDDEN
        assert client.post(url, source_data()).status_code == HTTPStatus.FORBIDDEN
        source.refresh_from_db()
        assert source.name == "Original"


class TestSourceDelete:
    def test_owner_deletes_source(self, client: Client) -> None:
        source = SourceFactory()
        login(client, source.calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:source_delete", kwargs={"pk": source.pk}),
        )

        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(
            "calendars:calendar_update",
            kwargs={"uuid": source.calendar.uuid},
        )
        assert not Source.objects.filter(pk=source.pk).exists()

    def test_get_is_not_allowed(self, client: Client) -> None:
        source = SourceFactory()
        login(client, source.calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.get(
            reverse("calendars:source_delete", kwargs={"pk": source.pk}),
        )

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
        assert Source.objects.filter(pk=source.pk).exists()

    def test_other_user_gets_404(self, client: Client) -> None:
        source = SourceFactory()
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)

        response = client.post(
            reverse("calendars:source_delete", kwargs={"pk": source.pk}),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert Source.objects.filter(pk=source.pk).exists()


class TestCalendarView:
    def test_anyone_can_view_calendar_page(self, client: Client) -> None:
        calendar = CalendarFactory(name="Shared schedule")

        response = client.get(
            reverse("calendars:calendar_view", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.OK
        assert "Shared schedule" in response.content.decode()

    def test_unknown_calendar_is_404(self, client: Client) -> None:
        response = client.get(
            reverse("calendars:calendar_view", kwargs={"uuid": uuid4()}),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCalendarIframe:
    def test_iframe_can_be_embedded_on_other_sites(self, client: Client) -> None:
        calendar = CalendarFactory()

        response = client.get(
            reverse("calendars:calendar_iframe", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.OK
        assert "X-Frame-Options" not in response.headers

    def test_unknown_calendar_is_404(self, client: Client) -> None:
        response = client.get(
            reverse(
                "calendars:calendar_iframe",
                kwargs={"uuid": uuid4()},
            ),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND


class TestCalendarRefresh:
    def test_owner_clears_cached_feed_and_returns_to_calendar(
        self,
        client: Client,
    ) -> None:
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.BUSINESS)
        cache.set(calendar_output_cache_key(calendar.uuid), "stale")

        response = client.post(
            reverse("calendars:calendar_refresh", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.FOUND
        assert response.url == reverse(
            "calendars:calendar_view",
            kwargs={"uuid": calendar.uuid},
        )
        assert cache.get(calendar_output_cache_key(calendar.uuid)) is None

    def test_other_user_gets_404_and_cache_is_kept(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, UserFactory(), User.SubscriptionTier.BUSINESS)
        cache.set(calendar_output_cache_key(calendar.uuid), "cached")

        response = client.post(
            reverse("calendars:calendar_refresh", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert cache.get(calendar_output_cache_key(calendar.uuid)) == "cached"

    def test_get_is_not_allowed(self, client: Client) -> None:
        calendar = CalendarFactory()
        login(client, calendar.owner, User.SubscriptionTier.BUSINESS)

        response = client.get(
            reverse("calendars:calendar_refresh", kwargs={"uuid": calendar.uuid}),
        )

        assert response.status_code == HTTPStatus.METHOD_NOT_ALLOWED
