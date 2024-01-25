import uuid
import zoneinfo

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from icalendar import Calendar as ical


def validate_ical_url(url):
    # if url[-5:] != ".ical":
    #    raise ValidationError(f'{url[-4:]} is not a valid calendar file extenstion')
    # if url is meetup.com skip Validation
    if "meetup.com" in url:
        return
    try:
        r = requests.get(url)
        r.raise_for_status()
        cal = ical.from_ical(r.text)  # noqa: F841
    except requests.exceptions.RequestException:
        raise ValidationError("Enter a valid URL")
    except ValueError:
        raise ValidationError("Enter a valid icalendar feed")


class Calendar(models.Model):
    name = models.CharField(max_length=255)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    # https://stackoverflow.com/a/70251235
    TIMEZONE_CHOICES = (
        (x, x) for x in sorted(zoneinfo.available_timezones(), key=str.lower)
    )
    timezone = models.CharField(
        "Timezone", choices=TIMEZONE_CHOICES, max_length=250, default="America/New_York"
    )
    calendar_file_str = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:calendar_detail", kwargs={"pk": self.pk})

    def get_calendar_file_url(self):
        return reverse("calendars:calendar_file", kwargs={"uuid": self.uuid})

    class Meta:
        ordering = ["-pk"]


class Source(models.Model):
    name = models.CharField(max_length=255)
    url = models.URLField(validators=[validate_ical_url])
    calendar = models.ForeignKey(
        "calendars.Calendar", on_delete=models.CASCADE, related_name="calendarOf"
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:source_detail", kwargs={"pk": self.pk})
