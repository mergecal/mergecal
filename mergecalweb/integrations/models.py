from django.db import models

from mergecalweb.calendars.models import Calendar
from mergecalweb.core.models import TimeStampedModel


class GoogleCalendarSync(TimeStampedModel):
    calendar = models.OneToOneField(
        Calendar,
        on_delete=models.CASCADE,
        related_name="google_calendar",
    )
    google_calendar_id = models.CharField(
        max_length=255,
        help_text="ID of the synchronized Google Calendar",
    )
    last_synced = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this calendar was synchronized",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Google Calendar Sync"
        verbose_name_plural = "Google Calendar Syncs"

    def __str__(self) -> str:
        return f"Google sync for {self.calendar.name}"
