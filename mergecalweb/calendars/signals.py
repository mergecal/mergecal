import logging

from django.core.cache import cache
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source

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
        "Signal: Source %s - source=%s, url=%s, calendar=%s, owner=%s",
        action,
        instance.name,
        instance.url,
        instance.calendar.name,
        instance.calendar.owner.username,
    )

    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info(
        "Cache invalidation: Source change - cache_key=%s, source=%s, action=%s",
        cache_key,
        instance.name,
        action,
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
        "Signal: Calendar %s - calendar=%s, uuid=%s, owner=%s",
        action,
        instance.name,
        instance.uuid,
        instance.owner.username,
    )

    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info(
        "Cache invalidation: Calendar change - cache_key=%s, calendar=%s, action=%s",
        cache_key,
        instance.name,
        action,
    )
