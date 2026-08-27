import logging

from django.db.models.signals import post_delete
from django.db.models.signals import post_save
from django.dispatch import receiver

from mergecalweb.calendars.cache import invalidate_calendar_cache
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.analytics import AnalyticsEvent
from mergecalweb.core.analytics import capture
from mergecalweb.core.analytics import set_person_properties
from mergecalweb.core.analytics import source_domain
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.core.utils import is_local_url

logger = logging.getLogger(__name__)


def _source_type(url: str) -> str:
    """Classify a source by where it comes from."""
    if "meetup.com" in url:
        return "meetup"
    if is_local_url(url):
        return "mergecal"
    return "remote"


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

    if action == "created":
        owner = calendar.owner
        capture(
            AnalyticsEvent.SOURCE_ADDED,
            # Named explicitly: sources are also created from the admin, where
            # the request context would name whoever is doing the creating.
            user=owner,
            calendar_uuid=str(calendar.uuid),
            source_domain=source_domain(instance.url),
            source_type=_source_type(instance.url),
            source_count=calendar.calendarOf.count(),
            # A user's first source anywhere is the closest thing the server
            # sees to activation.
            is_first_source=Source.objects.filter(calendar__owner=owner).count() == 1,
            user_tier=owner.subscription_tier,
        )

    invalidate_calendar_cache(calendar)


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

    if action == "created":
        owner = instance.owner
        calendar_count = owner.calendar_set.count()
        capture(
            AnalyticsEvent.CALENDAR_CREATED,
            user=owner,
            calendar_uuid=str(instance.uuid),
            calendar_count=calendar_count,
            is_first_calendar=calendar_count == 1,
            user_tier=owner.subscription_tier,
        )
        set_person_properties(owner, calendar_count=calendar_count)

    invalidate_calendar_cache(instance)
