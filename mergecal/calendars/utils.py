import logging
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from icalendar import Calendar, Event, Timezone

# Configure logging for the module
logger = logging.getLogger(__name__)


def combine_calendar(calendar_instance):
    newcal = Calendar()
    newcal.add("prodid", "-//" + calendar_instance.name + "//mergecal.habet.dev//")
    newcal.add("version", "2.0")
    newcal.add("x-wr-calname", calendar_instance.name)

    newtimezone = Timezone()
    newtimezone.add("tzid", calendar_instance.timezone)
    newcal.add_component(newtimezone)

    existing_uids = set()
    for source in calendar_instance.calendarOf.all():
        if is_meetup_url(source.url):
            logger.info(f"Meetup URL detected: {source.url}")
            try:
                meetup_group_name = extract_meetup_group_name(source.url)
                if meetup_group_name:
                    meetup_api_url = (
                        f"https://api.meetup.com/{meetup_group_name}/events"
                    )
                    response = requests.get(meetup_api_url)
                    response.raise_for_status()
                    meetup_events = response.json()
                    cal_data = create_calendar_from_meetup_api_respone(meetup_events)
                    if cal_data:
                        logger.info(f"Meetup events fetched: {len(meetup_events)}")
                        process_calendar_data(cal_data, newcal)
            except Exception as err:
                logger.error(f"Unexpected error with URL {source.url}: {err}")
        else:
            try:
                cal_data = fetch_calendar_data(source.url)
                if cal_data:
                    process_calendar_data(cal_data, newcal, existing_uids)
            except Exception as err:
                logger.error(f"Unexpected error with URL {source.url}: {err}")

    cal_bye_str = newcal.to_ical()
    calendar_instance.calendar_file_str = cal_bye_str.decode("utf8")
    calendar_instance.save()
    logger.info(
        f"Calendar for instance {calendar_instance.name} ({calendar_instance.uuid}) combined and saved."
    )


def fetch_calendar_data(url):
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",  # noqa: E501
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Connection": "keep-alive",
            "DNT": "1",  # Do Not Track Request Header
            "Upgrade-Insecure-Requests": "1",
        }

        response = requests.get(url, headers=headers)
        response.encoding = "utf-8"
        response.raise_for_status()
        return Calendar.from_ical(response.text)
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error fetching URL {url}: {err}")
    except ValueError as err:
        logger.error(f"Value error parsing URL {url}: {err}")
    except Exception as err:
        logger.error(f"Unexpected error fetching URL {url}: {err}")
    return None


def process_calendar_data(cal, newcal, existing_uids):
    for component in cal.subcomponents:
        if component.name == "VEVENT":
            uid = component.get("uid")
            # Add the event if it has a unique UID or if it doesn't have a UID at all
            if uid is None or uid not in existing_uids:
                newcal.add_component(component)
                if uid is not None:
                    existing_uids.add(uid)


def is_meetup_url(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Check if the domain is 'meetup.com'
    return parsed_url.netloc.endswith("meetup.com")


def extract_meetup_group_name(url):
    # Parse the URL
    parsed_url = urlparse(url)

    # Split the path into segments
    path_segments = parsed_url.path.split("/")

    # The group name should be the second segment in the path (after 'meetup.com/')
    if len(path_segments) >= 2:
        return path_segments[1]
    else:
        return None


def create_calendar_from_meetup_api_respone(events):
    # Create a calendar
    cal = Calendar()

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
                (event["time"] + event["duration"]) / 1000, tz=pytz.utc
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
