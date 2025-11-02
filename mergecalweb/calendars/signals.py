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
    # Construct the cache key similar to how you set it
    cache_key = f"calendar_str_{instance.calendar.uuid}"

    if kwargs.get("created") is not None:
        action = "created" if kwargs.get("created") else "updated"
    else:
        action = "deleted"

    logger.info(
        "Source %s",
        action,
        extra={
            "event": LogEvent.SOURCE_ADDED
            if action == "created"
            else (
                LogEvent.SOURCE_UPDATED
                if action == "updated"
                else LogEvent.SOURCE_DELETED
            ),
            "source_id": instance.pk,
            "source_url": instance.url,
            "source_name": instance.name,
            "calendar_uuid": instance.calendar.uuid,
            "calendar_name": instance.calendar.name,
            "user_id": instance.calendar.owner.pk,
            "email": instance.calendar.owner.email,
        },
    )

    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info(
        "Cache invalidated due to source change",
        extra={
            "event": LogEvent.CACHE_INVALIDATED_SOURCE_CHANGE,
            "cache_key": cache_key,
            "source_id": instance.pk,
            "source_name": instance.name,
            "action": action,
            "calendar_uuid": instance.calendar.uuid,
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
            "event": LogEvent.CALENDAR_CREATED
            if action == "created"
            else (
                LogEvent.CALENDAR_UPDATED
                if action == "updated"
                else LogEvent.CALENDAR_DELETED
            ),
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
            "event": LogEvent.CACHE_INVALIDATED_CALENDAR_CHANGE,
            "cache_key": cache_key,
            "calendar_uuid": instance.uuid,
            "calendar_name": instance.name,
            "action": action,
        },
    )
