"""Background pre-warming of merged-calendar caches for opted-in users.

Runs on a cron (outside the Gunicorn request budget) so each source can be
fetched with a generous timeout. For every opted-in calendar it drops the
merged-output cache and regenerates it via the normal merge pipeline, leaving
the per-source caches intact as a last-good fallback. When a real request
arrives it hits a warm, clean output cache and makes no live fetch.
"""

import logging
import time

from django.conf import settings
from django.core.cache import cache
from django.core.management.base import BaseCommand

from mergecalweb.calendars.cache import calendar_output_cache_key
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Pre-warm merged-calendar caches for opted-in users (run via cron)."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List the calendars that would be warmed without fetching.",
        )

    def _opted_in_calendars(self):
        user_ids = settings.CALENDAR_PREFETCH_USER_IDS
        if not user_ids:
            return Calendar.objects.none()

        return (
            Calendar.objects.filter(owner__id__in=user_ids)
            .exclude(owner__subscription_tier=User.SubscriptionTier.FREE)
            .select_related("owner")
            .prefetch_related("calendarOf")
            .order_by("pk")
        )

    def handle(self, *args, **options) -> None:
        dry_run = options["dry_run"]
        timeout = settings.CALENDAR_PREFETCH_TIMEOUT
        calendars = list(self._opted_in_calendars())

        logger.info(
            "Calendar prefetch starting",
            extra={
                "event": LogEvent.CALENDAR_TASK,
                "task_type": "prefetch",
                "status": "start",
                "total_calendars": len(calendars),
                "dry_run": dry_run,
            },
        )
        self.stdout.write(
            f"Prefetch: {len(calendars)} calendar(s) for "
            f"{len(settings.CALENDAR_PREFETCH_USER_IDS)} opted-in user(s)"
            + (" [dry-run]" if dry_run else ""),
        )

        succeeded = 0
        failed = 0
        for calendar in calendars:
            if dry_run:
                self.stdout.write(
                    f"  would warm {calendar.uuid} '{calendar.name}' "
                    f"(owner={calendar.owner.email}, "
                    f"sources={calendar.calendarOf.count()})",
                )
                continue

            if self._prefetch_one(calendar, timeout):
                succeeded += 1
            else:
                failed += 1

        logger.info(
            "Calendar prefetch finished",
            extra={
                "event": LogEvent.CALENDAR_TASK,
                "task_type": "prefetch",
                "status": "success",
                "total_calendars": len(calendars),
                "succeeded": succeeded,
                "failed": failed,
                "dry_run": dry_run,
            },
        )
        if not dry_run:
            self.stdout.write(
                f"Prefetch done: {succeeded} succeeded, {failed} failed",
            )

    def _prefetch_one(self, calendar: Calendar, timeout: int) -> bool:
        start_time = time.time()
        try:
            # Drop only the merged-output cache; keep per-source caches so a
            # momentarily-down source falls back to its last-good copy instead
            # of producing an error event.
            cache.delete(calendar_output_cache_key(calendar.uuid))
            calendar_str = CalendarMergerService(
                calendar,
                source_timeout=timeout,
            ).merge()
        except Exception:
            logger.exception(
                "Calendar prefetch failed",
                extra={
                    "event": LogEvent.CALENDAR_TASK,
                    "task_type": "prefetch",
                    "status": "error",
                    "calendar_uuid": calendar.uuid,
                    "calendar_name": calendar.name,
                    "duration_seconds": round(time.time() - start_time, 2),
                },
            )
            return False

        logger.info(
            "Calendar prefetched",
            extra={
                "event": LogEvent.CALENDAR_TASK,
                "task_type": "prefetch",
                "status": "success",
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "size_bytes": len(calendar_str),
                "duration_seconds": round(time.time() - start_time, 2),
            },
        )
        return True
