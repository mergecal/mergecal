import logging

from django.core.cache import cache
from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from mergecal.calendars.models import Calendar
from mergecal.calendars.models import Source

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Source)
@receiver(post_delete, sender=Source)
def clear_calendar_cache(sender, instance, **kwargs):
    # Construct the cache key similar to how you set it
    cache_key = f"calendar_str_{instance.calendar.uuid}"
    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info("Cache cleared for key: %s", cache_key)


@receiver(post_save, sender=Calendar)
@receiver(post_delete, sender=Calendar)
def clear_source_cache(sender, instance, **kwargs):
    # Construct the cache key similar to how you set it
    cache_key = f"calendar_str_{instance.uuid}"
    # Check if the cache exists and delete it
    cache.delete(cache_key)
    logger.info("Cache cleared for key: %s", cache_key)
