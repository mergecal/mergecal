# ruff: noqa: PLR0912, ERA001, PLR0915

import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

import requests
from django.core.cache import cache
from django.utils import timezone
from icalendar import Calendar
from icalendar import Timezone
from icalendar import TimezoneStandard

from mergecal.calendars.meetup import fetch_and_create_meetup_calendar
from mergecal.calendars.meetup import is_meetup_url

logger = logging.getLogger(__name__)


def combine_calendar(calendar_instance, origin_domain):
    cal_bye_str = cache.get(f"calendar_str_{calendar_instance.uuid}")
    if not cal_bye_str:
        logger.info(
            "Calendar data not found in cache, generating new for UUID: %s",
            calendar_instance.uuid,
        )
        newcal = Calendar()
        newcal.add("prodid", "-//" + calendar_instance.name + "//mergecal.org//")
        newcal.add("version", "2.0")
        newcal.add("x-wr-calname", calendar_instance.name)

        # Create and add the timezone component
        tzinfo = ZoneInfo(calendar_instance.timezone)
        newtimezone = Timezone()
        newtimezone.add("tzid", tzinfo.key)

        # Using Django's timezone.now() to get a timezone-aware datetime object
        now = timezone.now()
        std = TimezoneStandard()
        std.add(
            "dtstart",
            now - timedelta(days=1),
        )  # Setting dtstart to the previous day
        std.add("tzoffsetfrom", timedelta(seconds=-now.utcoffset().total_seconds()))
        std.add("tzoffsetto", timedelta(seconds=-now.utcoffset().total_seconds()))
        newtimezone.add_component(std)

        newcal.add_component(newtimezone)

        include_source = calendar_instance.include_source

        existing_uids = set()

        warning_text = ""
        if origin_domain in ["calmerge.habet.dev", "mergecal.habet.dev"]:
            warning_text = " Note: You are using an outdated domain. Please update to mergecal.org."  # noqa: E501

        for source in calendar_instance.calendarOf.all():
            cal_data = None
            if is_meetup_url(source.url):
                logger.info("Meetup URL detected: %s", source.url)
                cal_data = fetch_and_create_meetup_calendar(source.url)
            else:
                try:
                    cal_data = fetch_calendar_data(source.url)
                except Exception:
                    logger.exception(
                        "Fetching Cal: Unexpected error with URL %s",
                        source.url,
                    )
            if cal_data:
                process_calendar_data(
                    cal_data,
                    newcal,
                    existing_uids,
                    include_source,
                    source.name,
                    warning_text,
                )

        cal_bye_str = newcal.to_ical().decode("utf8")
        calendar_instance.calendar_file_str = cal_bye_str
        calendar_instance.save()
        cache.set(f"calendar_str_{calendar_instance.uuid}", cal_bye_str, 60 * 60 * 24)
        logger.info(
            "Calendar for instance %s (%s) combined and saved.",
            calendar_instance.name,
            calendar_instance.uuid,
        )
    else:
        logger.info("Calendar data found in cache for UUID: %s", calendar_instance.uuid)

    return cal_bye_str


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
            # component["description"] = f"{warning_text}\n\n{description}"
            advertisement = "\nThis event is brought to you by https://mergecal.org."
            if component.get("description"):
                component["description"] = component["description"] + advertisement
            else:
                component.add("description", advertisement)

            # Add the event if it has a unique UID or if it doesn't have a UID at all
            if uid is None or uid not in existing_uids:
                newcal.add_component(component)
                if uid is not None:
                    existing_uids.add(uid)
