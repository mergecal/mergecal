import uuid
import zoneinfo

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from icalendar import Calendar as Ical
from requests.exceptions import RequestException


def validate_ical_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa: E501
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "DNT": "1",  # Do Not Track Request Header
        "Upgrade-Insecure-Requests": "1",
    }

    # if url is meetup.com, skip validation
    if "meetup.com" in url:
        return

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        cal = Ical.from_ical(response.text)  # noqa: F841
    except RequestException as err:
        msg = "Enter a valid URL"
        raise ValidationError(msg) from err
    except ValueError as err:
        msg = "Enter a valid iCalendar feed"
        raise ValidationError(msg) from err


class Calendar(models.Model):
    name = models.CharField(max_length=255)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    # https://stackoverflow.com/a/70251235
    TIMEZONE_CHOICES = tuple(
        (x, x)
        for x in sorted(zoneinfo.available_timezones(), key=str.lower)
        if x != "localtime"  # Exclude 'localtime' from the choices
    )

    timezone = models.CharField(
        "Timezone",
        choices=TIMEZONE_CHOICES,
        max_length=250,
        default="America/New_York",
    )
    calendar_file_str = models.TextField(blank=True, null=True)  # noqa: DJ001
    # a boolean weather to include the source name in the event title
    include_source = models.BooleanField(
        default=False,
        help_text="Include source name in event title",
    )

    class Meta:
        ordering = ["-pk"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:calendar_detail", kwargs={"pk": self.pk})

    def get_calendar_file_url(self):
        return reverse("calendars:calendar_file", kwargs={"uuid": self.uuid})

    def get_calendar_view_url(self):
        return reverse("calendars:calendar-view", kwargs={"uuid": self.uuid})


class Source(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(max_length=400, validators=[validate_ical_url])
    calendar = models.ForeignKey(
        "calendars.Calendar",
        on_delete=models.CASCADE,
        related_name="calendarOf",
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:source_detail", kwargs={"pk": self.pk})
