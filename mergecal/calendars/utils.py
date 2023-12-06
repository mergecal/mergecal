import logging

import requests
from icalendar import Calendar, Timezone

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

    for source in calendar_instance.calendarOf.all():
        try:
            cal_data = fetch_calendar_data(source.url)
            if cal_data:
                process_calendar_data(cal_data, newcal)
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
        response = requests.get(url)
        response.raise_for_status()
        return Calendar.from_ical(response.text)
    except requests.exceptions.HTTPError as err:
        logger.error(f"HTTP error fetching URL {url}: {err}")
    except ValueError as err:
        logger.error(f"Value error parsing URL {url}: {err}")
    except Exception as err:
        logger.error(f"Unexpected error fetching URL {url}: {err}")
    return None


def process_calendar_data(cal, newcal):
    for component in cal.subcomponents:
        if component.name == "VEVENT":
            newcal.add_component(component)
