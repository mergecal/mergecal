from __future__ import annotations

import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Case
from django.db.models import IntegerField
from django.db.models import Value
from django.db.models import When

from mergecalweb.calendars.fetching.fetcher import CalendarFetcher
from mergecalweb.calendars.models import Calendar
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)

TIER_PRIORITY = Case(
    When(owner__subscription_tier=User.SubscriptionTier.SUPPORTER, then=Value(0)),
    When(owner__subscription_tier=User.SubscriptionTier.BUSINESS, then=Value(1)),
    When(owner__subscription_tier=User.SubscriptionTier.PERSONAL, then=Value(2)),
    default=Value(3),
    output_field=IntegerField(),
)


class Command(BaseCommand):
    help = "Prefetch and cache source calendar URLs for configured premium users."

    def handle(self, *args, **options) -> None:
        user_ids: list[int] = settings.CALENDAR_PREFETCH_USER_IDS
        if not user_ids:
            self.stdout.write("No users configured in CALENDAR_PREFETCH_USER_IDS.")
            return

        calendars = (
            Calendar.objects.filter(owner_id__in=user_ids)
            .select_related("owner")
            .annotate(tier_priority=TIER_PRIORITY)
            .order_by("tier_priority", "id")
            .prefetch_related("calendarOf")
        )

        total_calendars = calendars.count()
        logger.info(
            "Calendar prefetch started",
            extra={
                "event": LogEvent.CALENDAR_PREFETCH,
                "status": "start",
                "user_ids": user_ids,
                "total_calendars": total_calendars,
            },
        )

        fetcher = CalendarFetcher()
        total_fetched = 0
        total_errors = 0

        for calendar in calendars:
            fetched, errors = self._prefetch_calendar(fetcher, calendar)
            total_fetched += fetched
            total_errors += errors

        logger.info(
            "Calendar prefetch completed",
            extra={
                "event": LogEvent.CALENDAR_PREFETCH,
                "status": "success",
                "total_calendars": total_calendars,
                "total_fetched": total_fetched,
                "total_errors": total_errors,
            },
        )
        self.stdout.write(
            f"Done. {total_calendars} calendars, "
            f"{total_fetched} sources fetched, {total_errors} errors.",
        )

    def _prefetch_calendar(
        self,
        fetcher: CalendarFetcher,
        calendar: Calendar,
    ) -> tuple[int, int]:
        sources = calendar.calendarOf.all()
        fetched = 0
        errors = 0

        for source in sources:
            start = time.time()
            try:
                fetcher.fetch_calendar(source.url, force_refresh=True)
                fetched += 1
                logger.info(
                    "Prefetched source URL",
                    extra={
                        "event": LogEvent.CALENDAR_PREFETCH,
                        "status": "source-fetched",
                        "calendar_id": calendar.pk,
                        "calendar_uuid": str(calendar.uuid),
                        "source_id": source.pk,
                        "source_url": source.url[:200],
                        "duration_seconds": round(time.time() - start, 2),
                    },
                )
            except requests.RequestException as e:
                errors += 1
                logger.warning(
                    "Prefetch failed for source URL",
                    extra={
                        "event": LogEvent.CALENDAR_PREFETCH,
                        "status": "error",
                        "calendar_id": calendar.pk,
                        "calendar_uuid": str(calendar.uuid),
                        "owner_id": calendar.owner.pk,
                        "source_id": source.pk,
                        "source_url": source.url[:200],
                        "error_type": type(e).__name__,
                        "error": str(e),
                    },
                )

        return fetched, errors
