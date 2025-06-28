import hashlib
import logging
from datetime import UTC
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from typing import Any

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from icalendar import Event
from icalendar.prop import vDuration

from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService
from mergecalweb.integrations.models import GoogleCalendarSync
from mergecalweb.integrations.services.google_api import CalendarColors
from mergecalweb.integrations.services.google_api import GoogleApiClient
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class MissingGoogleCalendarRecordError(ObjectDoesNotExist):
    """
    Raised when GoogleCalendarSync record is missing
    and attempting to sync a MergeCal calendar
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
        self.sync: GoogleCalendarSync | None = None
        # Track events for logging/reporting
        self.added_events: list[dict[str, Any]] = []
        self.modified_events: list[dict[str, Any]] = []
        self.removed_events: list[dict[str, Any]] = []

    def _get_google_calendar_sync(self) -> GoogleCalendarSync:
        try:
            self.sync = GoogleCalendarSync.objects.get(calendar=self.calendar)
        except GoogleCalendarSync.DoesNotExist as e:
            msg = (
                f"GoogleCalendarSync record not found for calendar {self.calendar.name}"
            )
            raise MissingGoogleCalendarRecordError(msg) from e
        return self.sync

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
                self.sync = self.update_google_calendar(colors)
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

        self.sync = GoogleCalendarSync.objects.create(
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
        sync_record = self._get_google_calendar_sync()
        logger.info(
            "Updating Google Calendar (ID: %s) for MergeCal calendar '%s' (UUID: %s)",
            sync_record.google_calendar_id,
            calendar.name,
            calendar.uuid,
        )

        calendar_data = self._build_calendar_data(colors)
        self.api_client.update_calendar(sync_record.google_calendar_id, calendar_data)

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
                value = event.get(field)
                if field in ["dtstart", "dtend"]:
                    dt = value.dt if hasattr(value, "dt") else value
                    # Normalize timezone for consistent hashing
                    if isinstance(dt, datetime):
                        dt = dt.astimezone(UTC)
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

    def _build_event_data(
        self,
        event: Event,
        event_id: str,
        event_hash: str,
    ) -> dict[str, Any]:
        """Convert an iCalendar Event to Google Calendar event format.

        Args:
            event: The iCalendar Event object to convert
            event_id: Unique identifier for the event
            event_hash: Hash of event content for change detection

        Returns:
            dict: Event data formatted for Google Calendar API

        Raises:
            ValueError: If required event data is missing or invalid
        """
        # Core event data
        event_data = {
            "summary": str(event.get("summary", "Untitled Event")),
            "description": str(event.get("description", "")),
            "location": str(event.get("location", "")),
            "extendedProperties": {
                "private": {
                    self.MERGECAL_EVENT_ID: event_id,
                    self.EVENT_HASH: event_hash,
                    self.FROM_MERGECAL: "true",
                },
            },
        }

        # Handle start/end times - this needs to succeed for a valid event
        start = event.decoded("dtstart")
        if "dtend" in event:
            end = event.decoded("dtend")
        elif "duration" in event:
            end = start + event.decoded("duration")
        else:
            end = start

        # Format for Google Calendar API
        if isinstance(start, datetime):
            if not start.tzinfo:
                start = self.calendar.timezone.localize(start)
            if not end.tzinfo:
                end = self.calendar.timezone.localize(end)

            event_data["start"] = {
                "dateTime": start.isoformat(),
                "timeZone": self.calendar.timezone,
            }
            event_data["end"] = {
                "dateTime": end.isoformat(),
                "timeZone": self.calendar.timezone,
            }
        else:
            # All-day event
            event_data["start"] = {"date": start.isoformat()}
            event_data["end"] = {"date": end.isoformat()}

        # Status mapping
        if "status" in event:
            status = str(event["status"]).upper()
            status_map = {
                "TENTATIVE": "tentative",
                "CONFIRMED": "confirmed",
                "CANCELLED": "cancelled",
            }
            event_data["status"] = status_map.get(status, "confirmed")

        # Transparency mapping
        if "transp" in event:
            transp = str(event["transp"]).upper()
            transp_map = {"TRANSPARENT": "transparent", "OPAQUE": "opaque"}
            event_data["transparency"] = transp_map.get(transp, "opaque")

        # Visibility mapping
        if "class" in event:
            event_class = str(event["class"]).upper()
            class_map = {
                "PUBLIC": "public",
                "PRIVATE": "private",
                "CONFIDENTIAL": "private",
            }
            event_data["visibility"] = class_map.get(event_class, "default")

        # Recurrence rules
        recurrence = []
        for prop in ("rrule", "exrule", "rdate", "exdate"):
            if prop in event:
                val = event[prop]
                if not isinstance(val, list):
                    val = [val]
                for v in val:
                    recurrence.append(f"{prop.upper()}:{v.to_ical().decode()}")
        if recurrence:
            event_data["recurrence"] = recurrence

        # Reminders
        reminders = []
        for alarm in event.walk("valarm"):
            trigger = alarm.get("trigger")
            if not trigger or not hasattr(trigger, "dt"):
                continue

            if isinstance(trigger.dt, timedelta):
                minutes = int(trigger.dt.total_seconds() / 60)
                if 0 <= abs(minutes) <= 40320:  # Max 4 weeks
                    reminders.append({"method": "popup", "minutes": abs(minutes)})

        if reminders:
            event_data["reminders"] = {
                "useDefault": False,
                "overrides": sorted(reminders, key=lambda x: x["minutes"])[:5],
            }
        else:
            event_data["reminders"] = {"useDefault": True}

        # Attendees
        if "attendee" in event:
            attendees = []
            attendee_list = event["attendee"]
            if not isinstance(attendee_list, list):
                attendee_list = [attendee_list]

            for attendee in attendee_list:
                attendee_data = {"email": str(attendee).replace("mailto:", "")}

                params = attendee.params
                if "CN" in params:
                    attendee_data["displayName"] = params["CN"]
                if "PARTSTAT" in params:
                    partstat_map = {
                        "ACCEPTED": "accepted",
                        "DECLINED": "declined",
                        "TENTATIVE": "tentative",
                        "NEEDS-ACTION": "needsAction",
                    }
                    attendee_data["responseStatus"] = partstat_map.get(
                        params["PARTSTAT"],
                        "needsAction",
                    )
                if "ROLE" in params:
                    attendee_data["optional"] = params["ROLE"] != "REQ-PARTICIPANT"

                attendees.append(attendee_data)

            if attendees:
                event_data["attendees"] = attendees

        # Organizer
        if "organizer" in event:
            organizer = event["organizer"]
            event_data["organizer"] = {
                "email": str(organizer).replace("mailto:", ""),
                "displayName": organizer.params.get("CN", ""),
            }

        # Sequence number
        if "sequence" in event:
            event_data["sequence"] = event["sequence"]

        return event_data

    def sync_events(self) -> None:
        """Synchronize events from MergeCal calendar to Google Calendar."""
        ical = CalendarMergerService(self.calendar).get_merged_calendar()
        sync_record = self._get_google_calendar_sync()

        logger.info(
            "Starting event sync for calendar '%s' (Google Calendar ID: %s)",
            self.calendar.name,
            sync_record.google_calendar_id,
        )

        # Reset counters for this sync
        self.added_events = []
        self.modified_events = []
        self.removed_events = []

        with transaction.atomic():
            # Get all existing events from Google Calendar, including recurring instances
            google_events = self.api_client.list_events(
                sync_record.google_calendar_id,
                singleEvents=True,
                timeZone=self.calendar.timezone,
            )

            # Build map of event IDs to Google Calendar events
            google_events_map = {}
            mergecal_events_found = 0

            for event in google_events:
                ext_props = event.get("extendedProperties", {}).get("private", {})
                if ext_props.get(self.FROM_MERGECAL):
                    mergecal_id = ext_props.get(self.MERGECAL_EVENT_ID)
                    if mergecal_id:
                        google_events_map[mergecal_id] = event
                        mergecal_events_found += 1

            logger.info(
                "Found %d total events in Google Calendar, %d are from MergeCal",
                len(google_events),
                mergecal_events_found,
            )

            # Process each MergeCal event
            mergecal_event_ids = []
            for event in ical.events:
                # Get or generate event ID
                event_id = event.get("uid")
                if not event_id:
                    event_id = hashlib.md5(str(event).encode()).hexdigest()

                # Handle recurrence exceptions
                recurrence_id = event.get("recurrence-id")
                if recurrence_id:
                    event_id = f"{event_id}_{recurrence_id}"

                mergecal_event_ids.append(event_id)
                event_hash = self._calculate_event_hash(event)

                google_event = google_events_map.get(event_id)

                if google_event:
                    existing_hash = (
                        google_event.get("extendedProperties", {})
                        .get("private", {})
                        .get(self.EVENT_HASH)
                    )

                    if existing_hash != event_hash:
                        self._update_event(
                            sync_record.google_calendar_id,
                            google_event["id"],
                            event,
                            event_id,
                            event_hash,
                        )
                else:
                    self._create_event(
                        sync_record.google_calendar_id,
                        event,
                        event_id,
                        event_hash,
                    )

            # Handle cleanup
            self._cleanup_events(
                sync_record.google_calendar_id,
                google_events_map,
                mergecal_event_ids,
            )

            # Update sync timestamp
            sync_record.last_synced = datetime.now(UTC)
            sync_record.save()

            logger.info(
                "Sync completed for calendar '%s'. Added: %d, Modified: %d, Removed: %d",
                self.calendar.name,
                len(self.added_events),
                len(self.modified_events),
                len(self.removed_events),
            )

    def _create_event(
        self,
        calendar_id: str,
        event: Event,
        event_id: str,
        event_hash: str,
    ) -> None:
        """Create a new event in Google Calendar."""
        event_data = self._build_event_data(event, event_id, event_hash)
        logger.info("Creating new event '%s'", event_data.get("summary", "Untitled"))
        created_event = self.api_client.create_event(calendar_id, event_data)
        self.added_events.append(created_event)

    def _update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: Event,
        mergecal_event_id: str,
        event_hash: str,
    ) -> None:
        """Update an existing event in Google Calendar."""
        event_data = self._build_event_data(event, mergecal_event_id, event_hash)
        logger.info("Updating event '%s'", event_data.get("summary", "Untitled"))
        updated_event = self.api_client.update_event(calendar_id, event_id, event_data)
        self.modified_events.append(updated_event)

    def _cleanup_events(
        self,
        calendar_id: str,
        google_events: dict[str, Any],
        mergecal_event_ids: list[str],
    ) -> None:
        """Remove events from Google Calendar that no longer exist in MergeCal."""
        for event_id, event in google_events.items():
            if event_id not in mergecal_event_ids:
                logger.info(
                    "Removing deleted event '%s'",
                    event.get("summary", "Untitled"),
                )
                self.api_client.delete_event(calendar_id, event["id"])
                self.removed_events.append(event)
