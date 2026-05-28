import logging

from django.core.cache import cache
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.logging_events import LogEvent

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Source)
@receiver(post_delete, sender=Source)
def clear_calendar_cache_on_source(sender, instance, **kwargs):
    if kwargs.get("created") is not None:
        action = "created" if kwargs.get("created") else "updated"
    else:
        action = "deleted"

    # When a Calendar is deleted, its Sources are cascade-deleted.
    # The post_delete signal fires after the Calendar is already gone,
    # so accessing instance.calendar raises Calendar.DoesNotExist.
    # In this case, we skip cache invalidation here since the Calendar's
    # own post_delete signal (clear_calendar_cache_on_calendar) will handle it.
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

    # Construct the cache key similar to how you set it
    cache_key = f"calendar_str_{calendar.uuid}"

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

    # Clear the merged calendar string cache
    cache.delete(cache_key)
    logger.info(
        "Cache invalidated due to source change",
        extra={
            "event": LogEvent.CACHE_INVALIDATED,
            "cache_reason": "source-change",
            "cache_key": cache_key,
            "source_id": instance.pk,
            "source_name": instance.name,
            "action": action,
            "calendar_uuid": calendar.uuid,
        },
    )

    # Clear the source URL cache so the next fetch gets fresh content
    source_cache_key = f"calendar_data_{instance.url}"
    cache.delete(source_cache_key)
    logger.info(
        "Source URL cache invalidated",
        extra={
            "event": LogEvent.CACHE_INVALIDATED,
            "cache_reason": "source-change",
            "cache_key": source_cache_key,
            "source_id": instance.pk,
            "source_url": instance.url,
            "action": action,
            "calendar_uuid": calendar.uuid,
        },
    )


@receiver(post_save, sender=Calendar)
@receiver(post_delete, sender=Calendar)
def clear_calendar_cache_on_calendar(sender, instance, **kwargs):
    # Construct the cache key similar to how you set it
    cache_key = f"calendar_str_{instance.uuid}"

    if kwargs.get("created") is not None:
        action = "created" if kwargs.get("created") else "updated"
    else:
        action = "deleted"

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

    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info(
        "Cache invalidated due to calendar change",
        extra={
            "event": LogEvent.CACHE_INVALIDATED,
            "cache_reason": "calendar-change",
            "cache_key": cache_key,
            "calendar_uuid": instance.uuid,
            "calendar_name": instance.name,
            "action": action,
        },
    )
