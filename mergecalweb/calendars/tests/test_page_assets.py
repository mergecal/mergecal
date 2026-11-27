from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from django.urls import reverse

if TYPE_CHECKING:
    from django.test import Client

    from mergecalweb.calendars.models import Calendar

FULLCALENDAR = "fullcalendar-scheduler-6.1.15"


@pytest.fixture(autouse=True)
def _uncompressed_assets(settings) -> None:
    settings.COMPRESS_ENABLED = False


@pytest.mark.django_db
def test_calendar_dashboard_loads_calendar_scripts(
    authenticated_client: Client,
    calendar: Calendar,
) -> None:
    url = reverse("calendars:calendar_update", kwargs={"uuid": calendar.uuid})

    response = authenticated_client.get(url)

    assert FULLCALENDAR in response.content.decode()


@pytest.mark.django_db
def test_home_page_skips_calendar_scripts(client: Client) -> None:
    response = client.get(reverse("home"))

    assert FULLCALENDAR not in response.content.decode()
