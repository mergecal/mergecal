import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from urllib.parse import quote
from zoneinfo import ZoneInfo

from allauth.socialaccount.models import SocialApp
from allauth.socialaccount.models import SocialToken
from caldav import DAVClient
from caldav.requests import HTTPBearerAuth
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource
from googleapiclient.discovery import build

from mergecalweb.integrations.models import GoogleCalendarSync
from mergecalweb.users.models import User

logger = logging.getLogger(__name__)


class GoogleAccountNotConnectedError(Exception):
    """Exception raised when Google account is not connected for user"""


@dataclass
class CalendarColors:
    """Calendar color configuration"""

    foreground: str = "#000000"
    background: str = "#4285F4"


def get_credentials(user: User) -> Credentials:
    """Get Google OAuth2 credentials for the user"""
    token = SocialToken.objects.filter(
        account__user=user,
        account__provider="google",
    ).first()

    if not token:
        msg = "No Google account connected for user: %s", user
        raise GoogleAccountNotConnectedError(msg)

    google = SocialApp.objects.get(provider="google")
    credentials = Credentials(
        token=token.token,
        refresh_token=token.token_secret,
        client_id=google.client_id,
        client_secret=google.secret,
        token_uri="https://oauth2.googleapis.com/token",
    )

    # Check if token is expired and refresh if needed
    if token.expires_at and token.expires_at <= datetime.now(ZoneInfo("UTC")):
        credentials.refresh(Request())
        # Update the token in database
        token.token = credentials.token
        token.expires_at = datetime.fromtimestamp(
            credentials.expiry.timestamp(),
            tz=ZoneInfo("UTC"),
        )
        token.save()

    return credentials


class GoolgeCaldavClient:
    """Caldav client for Google Calendar"""

    def __init__(self, user: User, google_calendar_sync: GoogleCalendarSync) -> None:
        self.user = user
        self.google_calendar_sync: GoogleCalendarSync = google_calendar_sync
        self._client: DAVClient | None = None
        logger.debug(
            "Initialized GoogleCaldavclient for user: %s, sync: %s",
            user,
            google_calendar_sync,
        )

    @property
    def client(self) -> DAVClient:
        if self._client is not None:
            return self._client
        logger.debug(
            "Setting up Caldav client for user: %s, sync: %s",
            self.user,
            self.google_calendar_sync,
        )
        credentials = get_credentials(self.user)
        sync_record = self.google_calendar_sync
        return DAVClient(
            url=f"https://apidata.googleusercontent.com/caldav/v2/{quote(sync_record.google_calendar_id)}/events",
            auth=HTTPBearerAuth(credentials.token),
        )


class GoogleApiClient:
    """Client for all Google Calendar API interactions"""

    def __init__(self, user: User) -> None:
        self.user = user
        self._api_client: Resource | None = None
        logger.debug("Initialized Google API client for user: %s", user)

    @property
    def client(self) -> Resource:
        """Lazy initialization of Google Calendar API client"""
        if self._api_client is not None:
            return self._api_client

        logger.info("Setting up Google API client for user: %s", self.user)
        credentials = get_credentials(self.user)
        self._api_client = build("calendar", "v3", credentials=credentials)
        return self._api_client

    # Calendar Operations
    def create_calendar(self, calendar_data: dict) -> dict:
        """Create a new Google Calendar"""
        logger.info("Creating new Google Calendar")
        return self.client.calendars().insert(body=calendar_data).execute()

    def update_calendar(self, calendar_id: str, calendar_data: dict) -> dict:
        """Update an existing Google Calendar"""
        logger.info("Updating Google Calendar: %s", calendar_id)
        return (
            self.client.calendars()
            .update(calendarId=calendar_id, body=calendar_data)
            .execute()
        )

    def delete_calendar(self, calendar_id: str) -> None:
        """Delete a Google Calendar"""
        logger.info("Deleting Google Calendar: %s", calendar_id)
        self.client.calendars().delete(calendarId=calendar_id).execute()

    # Event Operations
    def list_events(
        self,
        calendar_id: str,
        time_min: datetime | None = None,
        time_max: datetime | None = None,
        max_results: int = 2500,
        **kwargs: Any,
    ) -> list[dict]:
        """List events in a calendar"""
        logger.info("Listing events for calendar: %s", calendar_id)

        params: dict[str, Any] = {
            "calendarId": calendar_id,
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min.isoformat()
        if time_max:
            params["timeMax"] = time_max.isoformat()

        params.update(kwargs)

        return self.client.events().list(**params).execute().get("items", [])

    def create_event(self, calendar_id: str, event_data: dict) -> dict:
        """Create a new event"""
        logger.info("Creating event in calendar: %s", calendar_id)
        return (
            self.client.events()
            .insert(calendarId=calendar_id, body=event_data)
            .execute()
        )

    def update_event(self, calendar_id: str, event_id: str, event_data: dict) -> dict:
        """Update an existing event"""
        logger.info("Updating event %s in calendar: %s", event_id, calendar_id)
        return (
            self.client.events()
            .update(calendarId=calendar_id, eventId=event_id, body=event_data)
            .execute()
        )

    def delete_event(self, calendar_id: str, event_id: str) -> None:
        """Delete an event"""
        logger.info("Deleting event %s from calendar: %s", event_id, calendar_id)
        self.client.events().delete(calendarId=calendar_id, eventId=event_id).execute()
