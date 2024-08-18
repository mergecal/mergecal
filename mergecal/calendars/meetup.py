import html
import logging
import re
from datetime import datetime
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup
from icalendar import Calendar as Ical
from icalendar import Event

logger = logging.getLogger(__name__)


def clean_meetup_description(description: str) -> str:
    # Unescape HTML entities
    text = html.unescape(description)

    # Parse with BeautifulSoup
    soup = BeautifulSoup(text, "html.parser")

    # Replace <br> tags with newlines
    for br in soup.find_all("br"):
        br.replace_with("\n")

    # Replace <p> tags with double newlines
    for p in soup.find_all("p"):
        p.replace_with(f"\n\n{p.get_text()}")

    # Get the text content
    text = soup.get_text()

    # Remove Markdown-style formatting
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)

    # Convert Markdown-style links to plain text
    text = re.sub(r"\[(.*?)\]\((.*?)\)", r"\1 (\2)", text)

    # Replace multiple spaces with a single space
    text = re.sub(r" +", " ", text)

    # Replace multiple newlines with a maximum of two
    text = re.sub(r"\n{3,}", "\n\n", text)

    # Ensure common symbols have a newline before them if not at the start of a line
    text = re.sub(r"(?<!\n)([⛔🍕🃏])", r"\n\1", text)

    return text.strip()


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


def create_calendar_from_meetup_api_response(events: list[dict[str, Any]]) -> Ical:
    cal = Ical()
    cal.add("prodid", "-//MergeCal//Meetup Calendar//EN")
    cal.add("version", "2.0")
    cal.add("x-wr-calname", "Meetup Events")

    for event in events:
        e = Event()

        # Basic event details
        e.add("summary", event["name"])
        e.add("uid", f"meetup-{event['id']}@mergecal.org")  # Use Meetup event ID as UID

        # Date and time
        start_time = datetime.fromtimestamp(event["time"] / 1000, tz=ZoneInfo("UTC"))
        e.add("dtstart", start_time)
        end_time = datetime.fromtimestamp(
            (event["time"] + event["duration"]) / 1000,
            tz=ZoneInfo("UTC"),
        )
        e.add("dtend", end_time)
        e.add(
            "dtstamp",
            datetime.fromtimestamp(event["updated"] / 1000, tz=ZoneInfo("UTC")),
        )

        # Description and URL
        description = clean_meetup_description(event["description"])
        if event.get("how_to_find_us"):
            description += f"\n\nHow to find us: {event['how_to_find_us']}"
        e.add("description", description)
        e.add("url", event["link"])

        # Location
        if "venue" in event:
            venue = event["venue"]
            location = f"{venue.get('name', '')}, {venue.get('address_1', '')}, {venue.get('city', '')}, {venue.get('state', '')}, {venue.get('country', '')}"  # noqa: E501
            e.add("location", location.strip(", "))
            if "lat" in venue and "lon" in venue:
                e.add("geo", (venue["lat"], venue["lon"]))

        # Status
        e.add("status", "CONFIRMED" if event["status"] == "upcoming" else "CANCELLED")

        # Organizer
        if "group" in event:
            e.add("organizer", f"CN={event['group']['name']}:mailto:noreply@meetup.com")

        # Categories
        if "group" in event and "who" in event["group"]:
            e.add("categories", event["group"]["who"])

        # Add custom Meetup-specific properties
        e.add("x-meetup-event-id", event["id"])
        e.add("x-meetup-group-id", str(event["group"]["id"]))
        e.add("x-meetup-rsvp-limit", str(event.get("rsvp_limit", "")))
        e.add("x-meetup-yes-rsvp-count", str(event.get("yes_rsvp_count", 0)))

        cal.add_component(e)

    return cal


def fetch_and_create_meetup_calendar(meetup_url: str) -> Ical | None:
    try:
        is_meetup_url(meetup_url)
        meetup_group_name = extract_meetup_group_name(meetup_url)
        meetup_api_url = f"https://api.meetup.com/{meetup_group_name}/events"
        response = requests.get(meetup_api_url, timeout=10)
        response.raise_for_status()
        meetup_events = response.json()
        return create_calendar_from_meetup_api_response(
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
