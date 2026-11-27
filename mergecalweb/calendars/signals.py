import logging

from django.core.cache import cache
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from mergecalweb.calendars.cache import calendar_output_cache_key
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Source)
@receiver(post_delete, sender=Source)
def clear_calendar_cache_on_source(sender, instance, **kwargs):
    action = (
        "created"
        if kwargs.get("created")
        else ("deleted" if kwargs.get("created") is None else "updated")
    )

    # When a Calendar is deleted, its Sources are cascade-deleted.
    # The post_delete signal fires after the Calendar is already gone,
    # so accessing instance.calendar raises Calendar.DoesNotExist.
    # Skip here — the Calendar's own post_delete signal handles invalidation.
    try:
        calendar = instance.calendar
    except Calendar.DoesNotExist:
        logger.info(
            "Source %s (calendar already deleted, skipping cache invalidation)",
            action,
            extra={
                "event": LogEvent.SOURCE_ACTION,
                "action": action,
                "source_id": instance.pk,
                "source_url": instance.url,
                "source_name": instance.name,
                "calendar_id": instance.calendar_id,
            },
        )
        return

    logger.info(
        "Source %s",
        action,
        extra={
            "event": LogEvent.SOURCE_ACTION,
            "action": action,
            "source_id": instance.pk,
            "source_url": instance.url,
            "source_name": instance.name,
            "calendar_uuid": calendar.uuid,
            "calendar_name": calendar.name,
            "user_id": calendar.owner.pk,
            "email": calendar.owner.email,
        },
    )
    # Only the merged output depends on a source's settings. The fetched feed
    # is keyed by URL, and validating a new URL has just cached it.
    cache.delete(calendar_output_cache_key(calendar.uuid))


@receiver(post_save, sender=Calendar)
@receiver(post_delete, sender=Calendar)
def clear_calendar_cache_on_calendar(sender, instance, **kwargs):
    action = (
        "created"
        if kwargs.get("created")
        else ("deleted" if kwargs.get("created") is None else "updated")
    )

    logger.info(
        "Calendar %s",
        action,
        extra={
            "event": LogEvent.CALENDAR_ACTION,
            "action": action,
            "calendar_uuid": instance.uuid,
            "calendar_name": instance.name,
            "user_id": instance.owner.pk,
            "email": instance.owner.email,
        },
    )
    cache.delete(calendar_output_cache_key(instance.uuid))
