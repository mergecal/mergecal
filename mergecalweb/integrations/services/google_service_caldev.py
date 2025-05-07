import hashlib
import logging
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.utils import timezone
from icalendar import Event
from icalendar.prop import vDuration

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService
from mergecalweb.integrations.models import GoogleCalendarSync
from mergecalweb.integrations.services.google_api import CalendarColors
from mergecalweb.integrations.services.google_api import GoogleApiClient
from mergecalweb.integrations.services.google_api import GoolgeCaldavClient
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
caldav = logging.getLogger("caldav")
caldav.setLevel(logging.DEBUG)


class MissingGoogleCalendarRecordError(ObjectDoesNotExist):
    """
    Raised when GoogleCalendarSync record is missing
    and attempting to sync a MergeCal calendar to Google
    """


class GoogleService:
    """Service for managing MergeCal calendar synchronization with Google Calendar"""

    # Properties we store in Google Calendar event's extendedProperties
    MERGECAL_EVENT_ID = "mergecal_event_id"
    EVENT_HASH = "mergecal_event_hash"
    FROM_MERGECAL = "from_mergecal"

    def __init__(self, calendar: Calendar) -> None:
        self.calendar = calendar
        self.user: User = calendar.owner
        self.api_client = GoogleApiClient(self.user)
        self._sync: GoogleCalendarSync | None = None
        self._caldav_client: GoolgeCaldavClient | None = None

    @property
    def sync(self) -> GoogleCalendarSync:
        if self._sync is None:
            try:
                self._sync = GoogleCalendarSync.objects.get(calendar=self.calendar)
            except GoogleCalendarSync.DoesNotExist as e:
                msg = f"GoogleCalendarSync record not found for calendar {self.calendar.name}"
                raise MissingGoogleCalendarRecordError(msg) from e
        return self._sync

    @property
    def caldav_client(self) -> GoolgeCaldavClient:
        if self._caldav_client is None:
            self._caldav_client = GoolgeCaldavClient(self.user, self.sync)
        return self._caldav_client

    def sync_calendar(
        self,
        colors: CalendarColors | None = None,
    ) -> GoogleCalendarSync:
        """
        Synchronize a MergeCal calendar with Google Calendar.
        Creates a new Google Calendar or updates existing one.
        """
        calendar = self.calendar
        colors = colors or CalendarColors()

        with transaction.atomic():
            # TODO: change to try except objectdoesnotexist
            sync_record = GoogleCalendarSync.objects.filter(calendar=calendar).first()

            if sync_record:
                self._sync = self.update_google_calendar(colors)
                return self.sync
            return self.create_google_calendar(colors)

    def create_google_calendar(
        self,
        colors: CalendarColors,
    ) -> GoogleCalendarSync:
        """Create a new Google Calendar and sync record"""
        calendar = self.calendar
        logger.info(
            "Creating Google Calendar for MergeCal calendar '%s' (UUID: %s)",
            calendar.name,
            calendar.uuid,
        )

        calendar_data = self._build_calendar_data(colors)
        google_calendar = self.api_client.create_calendar(calendar_data)

        self._sync = GoogleCalendarSync.objects.create(
            calendar=calendar,
            google_calendar_id=google_calendar["id"],
            last_synced=timezone.now(),
        )

        logger.info(
            "Successfully created Google Calendar (ID: %s) for MergeCal calendar '%s'",
            google_calendar["id"],
            calendar.name,
        )

        return self.sync

    def update_google_calendar(
        self,
        colors: CalendarColors,
    ) -> GoogleCalendarSync:
        """Update existing Google Calendar with latest MergeCal data"""
        calendar = self.calendar
        sync_record = self.sync
        logger.info(
            "Updating Google Calendar (ID: %s) for MergeCal calendar '%s' (UUID: %s)",
            sync_record.google_calendar_id,
            calendar.name,
            calendar.uuid,
        )

        calendar_data = self._build_calendar_data(colors)
        self.api_client.update_calendar(sync_record.google_calendar_id, calendar_data)

        # update last_synced to now
        # TODO: What constitutes a sync? perhaps we
        # should only update last_synced fro events
        sync_record.last_synced = timezone.now()
        sync_record.save()

        logger.info(
            "Successfully updated Google Calendar (ID: %s) for MergeCal calendar '%s'",
            sync_record.google_calendar_id,
            calendar.name,
        )

        return sync_record

    def _build_calendar_data(self, colors: CalendarColors) -> dict:
        """Build calendar data for Google Calendar API"""
        calendar = self.calendar
        return {
            "summary": f"MergeCal: {calendar.name}",
            "description": (
                f"Calendar synchronized from MergeCal (UUID: {calendar.uuid})\n"
                f"View original calendar: {calendar.get_calendar_view_url()}\n\n"
                "This calendar is automatically synchronized by MergeCal. "
                "Please do not edit events directly in this calendar."
            ),
            "timeZone": calendar.timezone,
            "foregroundColor": colors.foreground,
            "backgroundColor": colors.background,
        }

    def delete_google_calendar(self, sync_record: GoogleCalendarSync) -> None:
        """
        Delete a Google Calendar and its sync record

        Raises:
            HttpError: If Google Calendar API request fails
        """
        with transaction.atomic():
            self.api_client.delete_calendar(sync_record.google_calendar_id)
            sync_record.delete()

            logger.info(
                "Successfully deleted Google Calendar (ID: %s)",
                sync_record.google_calendar_id,
            )

    def _calculate_event_hash(self, event: Event) -> str:
        """
        Calculate a stable hash for an event based only on meaningful content.
        Adds proper handling of recurrence rules and exceptions.
        """
        logger.debug("Calculating hash for event: %s", event)
        hash_components = []

        # Core event fields
        fields_to_hash = [
            "summary",
            "description",
            "location",
            "dtstart",
            "dtend",
            "status",
            "transp",
        ]

        for field in fields_to_hash:
            if field in event:
                logger.debug("Processing field: %s", field)
                value = event.get(field)
                if field in ["dtstart", "dtend"]:
                    dt = value.dt if hasattr(value, "dt") else value
                    # Normalize timezone for consistent hashing
                    if isinstance(dt, datetime):
                        dt = dt.astimezone(ZoneInfo("UTC"))
                    hash_components.append(f"{field}:{dt.isoformat()}")
                else:
                    hash_components.append(f"{field}:{value}")

        # Add recurrence rules
        if "rrule" in event:
            hash_components.append(f"rrule:{event['rrule'].to_ical().decode()}")
        if "exdate" in event:
            hash_components.append(f"exdate:{event['exdate'].to_ical().decode()}")
        if "rdate" in event:
            hash_components.append(f"rdate:{event['rdate'].to_ical().decode()}")

        # Handle reminders
        for alarm in event.walk("valarm"):
            trigger = alarm.get("trigger")
            if isinstance(trigger, vDuration):
                minutes = int(trigger.dt.total_seconds() / 60)
                hash_components.append(f"alarm:{minutes}")

        hash_components.sort()
        hash_string = "|".join(hash_components)
        return hashlib.md5(hash_string.encode()).hexdigest()

    def sync_events(self) -> None:
        """Synchronize events from MergeCal calendar to Google Calendar using CalDAV."""
        merged_ical = CalendarMergerService(self.calendar).get_merged_calendar()

        logger.info(
            "Starting CalDAV event sync for calendar '%s' (Google Calendar ID: %s) user: %s",
            self.calendar.name,
            self.sync.google_calendar_id,
            self.user,
        )

        # Reset counters for this sync
        added_events = []
        modified_events = []
        removed_events = []

        client = self.caldav_client.client
        principal = client.principal()
        google_calendar = principal.calendars()[0]

        # Get existing events from Google Calendar
        existing_events = {}
        for event in google_calendar.events():
            event_uid = event.icalendar_component.get("UID")
            if event_uid:
                # Convert vText to string
                event_uid = str(event_uid).encode().decode("utf-8")
                existing_events[event_uid] = event

        logger.debug(
            "Fetched %d existing events from Google Calendar.",
            len(existing_events),
        )

        # Process each MergeCal event
        for vevent in merged_ical.events:
            event_id = vevent.get("uid", None)
            logger.debug("Processing event: %s", vevent.get("summary", "No summary"))

            if event_id in existing_events:
                google_event = existing_events[event_id]
                logger.debug("Found existing event with ID: %s", event_id)

                # Get existing hash directly from component
                existing_hash = google_event.icalendar_component.get(
                    "X-MERGECAL-HASH",
                    "",
                )
                existing_hash = (
                    str(existing_hash).encode().decode("utf-8") if existing_hash else ""
                )
                event_hash = self._calculate_event_hash(vevent)

                if existing_hash != event_hash:
                    # log both hashs
                    logger.debug(
                        "Existing hash: %s, New hash: %s",
                        existing_hash,
                        event_hash,
                    )
                    # Update event

                    vevent.add("x-mergecal-hash", event_hash)
                    logger.debug(
                        "Updating ICAL EVENT DATA: %s",
                        vevent.to_ical().decode("utf-8"),
                    )
                    google_event.data = vevent.to_ical().decode(
                        "utf-8",
                    )  # Let icalendar handle the encoding
                    google_event.save()
                    logger.debug("Updated event data: %s", google_event.data)
                    modified_events.append({"id": event_id})
                    logger.info("Updated event: %s", event_id)
                else:
                    logger.debug("No changes detected for event: %s", event_id)
            else:
                # Create new event
                logger.debug("Event ID %s not found in existing events.", event_id)
                if not event_id:  # Only generate a new UUID if there is no UID
                    event_id = str(uuid.uuid4())  # Generate a new UUID
                    vevent.add("uid", event_id)  # Add the new UUID as the UID
                    logger.info("Generated new UUID for event: %s", event_id)

                vevent.add(
                    "x-mergecal-hash",
                    self._calculate_event_hash(vevent),
                )  # Add hash for future comparison
                google_calendar.save_event(vevent.to_ical())
                added_events.append({"id": event_id})
                logger.info("Created new event: %s", event_id)

        # Remove deleted events
        mergecal_event_ids = {event.get("uid", "") for event in merged_ical.events}
        logger.debug(
            "Checking for events to delete. Current MergeCal event IDs: %s",
            mergecal_event_ids,
        )

        for event_id, google_event in existing_events.items():
            if event_id not in mergecal_event_ids:
                google_event.delete()
                removed_events.append({"id": event_id})
                logger.info("Deleted event: %s", event_id)
            else:
                logger.debug(
                    "Event ID %s is still present in MergeCal events.",
                    event_id,
                )

        # Update sync timestamp
        self.sync.last_synced = timezone.now()
        self.sync.save()
        logger.info("Updated sync timestamp for calendar '%s'.", self.calendar.name)

        logger.info(
            "CalDAV sync completed for calendar '%s'. Added: %d, Modified: %d, Removed: %d",
            self.calendar.name,
            len(added_events),
            len(modified_events),
            len(removed_events),
        )
