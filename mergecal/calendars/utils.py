# ruff: noqa: PLR0912

import logging
from datetime import datetime
from urllib.parse import urlparse

import pytz
import requests
from django.core.cache import cache
from icalendar import Calendar
from icalendar import Event
from icalendar import Timezone

logger = logging.getLogger(__name__)


def combine_calendar(calendar_instance, origin_domain):
    cal_bye_str = cache.get(f"calendar_str_{calendar_instance.uuid}")
    logger.info(
        "Calendar data not found in cache, generating new for UUID: %s",
        calendar_instance.uuid,
    )
    if not cal_bye_str:
        newcal = Calendar()
        newcal.add("prodid", "-//" + calendar_instance.name + "//mergecal.org//")
        newcal.add("version", "2.0")
        newcal.add("x-wr-calname", calendar_instance.name)

        newtimezone = Timezone()
        newtimezone.add("tzid", calendar_instance.timezone)
        newcal.add_component(newtimezone)

        include_source = calendar_instance.include_source

        existing_uids = set()

        warning_text = ""
        if origin_domain in ["calmerge.habet.dev", "mergecal.habet.dev"]:
            warning_text = " Note: You are using an outdated domain. Please update to mergecal.org."  # noqa: E501

        for source in calendar_instance.calendarOf.all():
            if is_meetup_url(source.url):
                logger.info("Meetup URL detected: %s", source.url)
                try:
                    meetup_group_name = extract_meetup_group_name(source.url)
                    if meetup_group_name:
                        meetup_api_url = (
                            f"https://api.meetup.com/{meetup_group_name}/events"
                        )
                        response = requests.get(meetup_api_url, timeout=10)
                        response.raise_for_status()
                        meetup_events = response.json()
                        cal_data = create_calendar_from_meetup_api_respone(
                            meetup_events,
                        )
                        if cal_data:
                            logger.info("Meetup events fetched: %s", len(meetup_events))
                            process_calendar_data(
                                cal_data,
                                newcal,
                                existing_uids,
                                include_source,
                                source.name,
                            )
                except Exception:
                    logger.exception("Meetup: Unexpected error with URL %s", source.url)
            else:
                try:
                    cal_data = fetch_calendar_data(source.url)
                    if cal_data:
                        process_calendar_data(
                            cal_data,
                            newcal,
                            existing_uids,
                            include_source,
                            source.name,
                            warning_text,
                        )
                except Exception:
                    logger.exception(
                        "Fetching Cal: Unexpected error with URL %s",
                        source.url,
                    )

        cal_bye_str = newcal.to_ical().decode("utf8")
        cache.set(f"calendar_str_{calendar_instance.uuid}", cal_bye_str, 60 * 60 * 24)
    else:
        logger.info("Calendar data found in cache for UUID: %s", calendar_instance.uuid)

    calendar_instance.calendar_file_str = cal_bye_str
    calendar_instance.save()
    logger.info(
        "Calendar for instance %s (%s) combined and saved.",
        calendar_instance.name,
        calendar_instance.uuid,
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

        response = requests.get(url, headers=headers, timeout=20)
        response.encoding = "utf-8"
        response.raise_for_status()
        return Calendar.from_ical(response.text)
    except requests.exceptions.HTTPError:
        logger.exception("HTTP error fetching URL %s", url)
    except ValueError:
        logger.exception("Value error parsing URL %s", url)
    except Exception:
        logger.exception("Unexpected error fetching URL %s", url)
    return None


def process_calendar_data(  # noqa: PLR0913
    cal,
    newcal,
    existing_uids,
    include_source,
    source_name,
    warning_text="",
):
    for component in cal.subcomponents:
        if component.name == "VEVENT":
            uid = component.get("uid")
            if include_source:
                original_summary = component.get("summary")
                component["summary"] = f"{source_name}: {original_summary}"
            # if warning_text != "":
            # component["description"] = f"{warning_text}\n\n{description}" # noqa: ERA001, E501
            advertisement = "\n This event is brought to you by https://mergecal.org."
            if component.get("description"):
                component["description"] = component["description"] + advertisement
            else:
                component.add("description", advertisement)

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
    if len(path_segments) >= 2:  # noqa: PLR2004
        return path_segments[1]
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
