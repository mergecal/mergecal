import hashlib
from dataclasses import dataclass
from datetime import date
from datetime import datetime
from datetime import timedelta

from googleapiclient.discovery import Resource


@dataclass
class CalendarEvent:
    id: str
    summary: str
    description: str | None
    location: str | None
    start: datetime | date  # Can be datetime or date for all-day events
    end: datetime | date  # Can be datetime or date for all-day events
    recurrence: list[str] | None
    attendees: list[dict] | None
    status: str = "confirmed"
    visibility: str = "default"
    is_all_day: bool = False


class CalendarSyncService:
    def __init__(self, google_service: Resource):
        self.service = google_service

    def sync_calendar(self, calendar_id: str, ical_calendar) -> None:
        """
        Syncs events from an iCal calendar to Google Calendar

        Args:
            calendar_id: Google Calendar ID to sync to
            ical_calendar: iCal calendar object containing events
        """
        # Get all existing Google Calendar events
        existing_events = self._get_existing_events(calendar_id)

        # Create maps for faster lookups
        existing_event_map = {
            event["extendedProperties"]["private"].get("ical_uid"): event
            for event in existing_events
            if event.get("extendedProperties", {}).get("private", {}).get("ical_uid")
        }

        event_md5_map = {
            event["extendedProperties"]["private"].get("ical_uid"): event[
                "extendedProperties"
            ]["private"].get("md5")
            for event in existing_events
            if event.get("extendedProperties", {}).get("private", {}).get("md5")
        }

        # Process each event from the iCal source
        for vevent in ical_calendar.walk("VEVENT"):
            event = self._parse_ical_event(vevent)
            if not event:  # Skip if parsing failed
                continue

            # Generate MD5 hash of event data for change detection
            event_data = f"{event.summary}{event.description}{event.location}{event.start}{event.end}"
            md5_hash = hashlib.md5(event_data.encode()).hexdigest()

            if event.id in existing_event_map:
                # Event exists - check if it needs updating
                if event_md5_map.get(event.id) != md5_hash:
                    self._update_event(
                        calendar_id,
                        existing_event_map[event.id]["id"],
                        event,
                        md5_hash,
                    )
            else:
                # New event - create it
                self._create_event(calendar_id, event, md5_hash)

        # Remove events that no longer exist in source
        current_event_ids = {
            vevent.get("uid")
            for vevent in ical_calendar.walk("VEVENT")
            if vevent.get("uid")
        }
        for google_event in existing_events:
            ical_uid = google_event["extendedProperties"]["private"].get("ical_uid")
            if ical_uid and ical_uid not in current_event_ids:
                self._delete_event(calendar_id, google_event["id"])

    def _get_existing_events(self, calendar_id: str) -> list[dict]:
        """Fetches all events from Google Calendar."""
        events = []
        page_token = None

        while True:
            response = (
                self.service.events()
                .list(
                    calendarId=calendar_id,
                    pageToken=page_token,
                    privateExtendedProperty="synced=true",
                )
                .execute()
            )

            events.extend(response["items"])
            page_token = response.get("nextPageToken")
            if not page_token:
                break

        return events

    def _parse_ical_event(self, vevent) -> CalendarEvent | None:
        """Converts an iCal event to our CalendarEvent model."""
        try:
            # Extract UID or generate one if missing
            event_uid = vevent.get("uid")
            if not event_uid:
                event_data = f"{vevent.get('summary', '')}{vevent.get('dtstart').dt}"
                event_uid = hashlib.md5(event_data.encode()).hexdigest()

            dtstart = vevent.get("dtstart")
            if not dtstart:
                return None

            start = dtstart.dt
            is_all_day = not isinstance(start, datetime)

            # Handle end time
            dtend = vevent.get("dtend")
            if dtend:
                end = dtend.dt
            else:
                # If no end time, check for duration
                duration = vevent.get("duration")
                if duration:
                    if is_all_day:
                        # For all-day events, duration is in days
                        end = start + timedelta(days=duration.dt.days)
                    else:
                        # For timed events, use the duration directly
                        end = start + duration.dt
                # If no duration either, use start time + 1 hour for timed events
                # or start date + 1 day for all-day events
                elif is_all_day:
                    end = start + timedelta(days=1)
                else:
                    end = start + timedelta(hours=1)

            return CalendarEvent(
                id=event_uid,
                summary=vevent.get("summary", "No Title"),
                description=vevent.get("description"),
                location=vevent.get("location"),
                start=start,
                end=end,
                recurrence=[str(rule) for rule in vevent.get("rrule", [])],
                attendees=[
                    {"email": attendee.value} for attendee in vevent.get("attendee", [])
                ],
                status=vevent.get("status", "confirmed").lower(),
                visibility=vevent.get("class", "default").lower(),
                is_all_day=is_all_day,
            )
        except Exception as e:
            logger.warning(f"Failed to parse iCal event: {e!s}")
            return None

    def _create_event(
        self,
        calendar_id: str,
        event: CalendarEvent,
        md5_hash: str,
    ) -> None:
        """Creates a new event in Google Calendar."""
        event_body = {
            "summary": event.summary,
            "description": event.description,
            "location": event.location,
            "status": event.status,
            "visibility": event.visibility,
            "extendedProperties": {
                "private": {"synced": "true", "ical_uid": event.id, "md5": md5_hash},
            },
        }

        # Handle all-day vs timed events
        if event.is_all_day:
            event_body["start"] = {"date": event.start.isoformat()}
            event_body["end"] = {"date": event.end.isoformat()}
        else:
            event_body["start"] = {"dateTime": event.start.isoformat()}
            event_body["end"] = {"dateTime": event.end.isoformat()}

        if event.recurrence:
            event_body["recurrence"] = event.recurrence
        if event.attendees:
            event_body["attendees"] = event.attendees

        self.service.events().insert(calendarId=calendar_id, body=event_body).execute()

    def _update_event(
        self,
        calendar_id: str,
        event_id: str,
        event: CalendarEvent,
        md5_hash: str,
    ) -> None:
        """Updates an existing event in Google Calendar."""
        event_body = {
            "summary": event.summary,
            "description": event.description,
            "location": event.location,
            "status": event.status,
            "visibility": event.visibility,
            "extendedProperties": {
                "private": {"synced": "true", "ical_uid": event.id, "md5": md5_hash},
            },
        }

        # Handle all-day vs timed events
        if event.is_all_day:
            event_body["start"] = {"date": event.start.isoformat()}
            event_body["end"] = {"date": event.end.isoformat()}
        else:
            event_body["start"] = {"dateTime": event.start.isoformat()}
            event_body["end"] = {"dateTime": event.end.isoformat()}

        if event.recurrence:
            event_body["recurrence"] = event.recurrence
        if event.attendees:
            event_body["attendees"] = event.attendees

        self.service.events().update(
            calendarId=calendar_id,
            eventId=event_id,
            body=event_body,
        ).execute()

    def _delete_event(self, calendar_id: str, event_id: str) -> None:
        """Deletes an event from Google Calendar."""
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
