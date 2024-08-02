import logging
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from icalendar import Calendar as Ical
from icalendar import Event

logger = logging.getLogger(__name__)


def is_meetup_url(url: str) -> bool:
    # Parse the URL
    parsed_url = urlparse(url)

    # Check if the domain is 'meetup.com'
    return parsed_url.netloc.endswith("meetup.com")


def extract_meetup_group_name(url: str) -> str | None:
    # Parse the URL
    parsed_url = urlparse(url)

    # Split the path into segments
    path_segments = parsed_url.path.split("/")

    # The group name should be the second segment in the path (after 'meetup.com/')
    if len(path_segments) >= 2:  # noqa: PLR2004
        return path_segments[1]
    msg = f"Unable to extract Meetup group name from URL: {url}"
    raise ValueError(msg)


def create_calendar_from_meetup_api_respone(events: list) -> Ical:
    # Create a calendar
    cal = Ical()

    # Set some global calendar properties
    cal.add("prodid", "-//My Calendar//mxm.dk//")
    cal.add("version", "2.0")

    for event in events:
        # Create an event
        e = Event()

        # Add event details
        e.add("summary", event["name"])
        e.add("dtstart", datetime.fromtimestamp(event["time"] / 1000, tz=pytz.utc))
        e.add(
            "dtend",
            datetime.fromtimestamp(
                (event["time"] + event["duration"]) / 1000,
                tz=pytz.utc,
            ),
        )
        e.add("dtstamp", datetime.fromtimestamp(event["created"] / 1000, tz=pytz.utc))
        e.add("description", event["description"])
        e.add("location", event.get("venue", {}).get("address_1", "No location"))
        e.add("url", event["link"])

        # Add event to calendar
        cal.add_component(e)

    # Return the calendar as a string
    return cal


def fetch_and_create_meetup_calendar(meetup_url: str) -> Ical | None:
    try:
        is_meetup_url(meetup_url)
        meetup_group_name = extract_meetup_group_name(meetup_url)
        meetup_api_url = f"https://api.meetup.com/{meetup_group_name}/events"
        response = requests.get(meetup_api_url, timeout=10)
        response.raise_for_status()
        meetup_events = response.json()
        return create_calendar_from_meetup_api_respone(
            meetup_events,
        )
    except requests.exceptions.HTTPError as e:
        logger.warning(
            "Meetup: Unable to fetch calendar from URL %s. HTTP error: %s",
            meetup_url,
            e,
        )
        return None
    except Exception:
        logger.exception("Meetup: Unexpected error with URL %s", meetup_url)
