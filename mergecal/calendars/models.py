# ruff: noqa: E501 ERA001
import uuid
import zoneinfo

import requests
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from icalendar import Calendar as Ical
from requests.exceptions import RequestException

from mergecal.core.models import TimeStampedModel

TWELVE_HOURS_IN_SECONDS = 43200


def validate_ical_url(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
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


class Calendar(TimeStampedModel):
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

    include_source = models.BooleanField(
        default=False,
        help_text="Include source name in event title",
    )
    update_frequency_seconds = models.PositiveIntegerField(
        _("Update Frequency"),
        default=TWELVE_HOURS_IN_SECONDS,  # 12 hours in seconds
        help_text=_(
            "How often the calendar updates in seconds. "
            "Default is every 12 hours (43200 seconds).",
        ),
    )
    remove_branding = models.BooleanField(
        _("Remove MergeCal Branding"),
        default=False,
        help_text=_(
            "Remove MergeCal branding from the calendar. "
            "Only available for Business tier and above.",
        ),
    )

    class Meta:
        ordering = ["-pk"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:calendar_update", kwargs={"uuid": self.uuid})

    def clean(self):
        if (
            not self.owner.can_set_update_frequency
            and self.update_frequency_seconds != TWELVE_HOURS_IN_SECONDS
        ):
            raise ValidationError(
                {
                    "update_frequency_seconds": _(
                        "You don't have permission to change the update frequency.",
                    ),
                },
            )
        if not self.owner.can_remove_branding and self.remove_branding:
            raise ValidationError(
                {"remove_branding": _("You don't have permission to remove branding.")},
            )

    @property
    def update_frequency_hours(self):
        return self.update_frequency_seconds // 3600

    @update_frequency_hours.setter
    def update_frequency_hours(self, hours):
        self.update_frequency_seconds = hours * 3600

    @property
    def effective_update_frequency(self):
        if self.owner.can_set_update_frequency:
            return self.update_frequency_seconds
        return TWELVE_HOURS_IN_SECONDS

    @property
    def show_branding(self):
        return not (self.remove_branding and self.owner.can_remove_branding)

    def get_calendar_file_url(self):
        return reverse("calendars:calendar_file", kwargs={"uuid": self.uuid})

    def get_calendar_view_url(self):
        return reverse("calendars:calendar-view", kwargs={"uuid": self.uuid})


class Source(TimeStampedModel):
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
        return reverse("calendars:source_edit", kwargs={"pk": self.pk})
