import logging
from datetime import timedelta
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from icalendar import Calendar as ICalendar
from icalendar import Event
from icalendar import Timezone
from icalendar import TimezoneStandard
from requests import RequestException
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mergecal.calendars.meetup import fetch_and_create_meetup_calendar
from mergecal.calendars.meetup import is_meetup_url

from .models import Calendar
from .models import Source

logger = logging.getLogger(__name__)


class CalendarMerger:
    def __init__(self, calendar: Calendar, request: HttpRequest):
        self.calendar = calendar
        self.request = request
        self.user = calendar.owner
        self.session = self._create_session()
        self.is_outdated_domain = self._check_outdated_domain()
        self.merged_calendar = None

    def merge(self) -> str:
        cache_key = f"calendar_str_{self.calendar.uuid}"
        cached_calendar = cache.get(cache_key)

        if cached_calendar is None:
            logger.debug(
                "Calendar data not found in cache, generating new for UUID: %s",
                self.calendar.uuid,
            )
            self.merged_calendar = self._create_new_calendar()
            self._add_sources()
            self._finalize_merged_calendar()
            calendar_str = self.merged_calendar.to_ical().decode("utf-8")
            self.calendar.calendar_file_str = calendar_str
            self.calendar.save()

            # Set cache with appropriate duration
            cache_duration = self.calendar.effective_update_frequency
            cache.set(cache_key, calendar_str, cache_duration)
        else:
            logger.debug(
                "Calendar data found in cache for UUID: %s",
                self.calendar.uuid,
            )
            calendar_str = cached_calendar

        return calendar_str

    def _check_outdated_domain(self) -> bool:
        origin_domain = self.request.GET.get("origin", "")
        return origin_domain in ["calmerge.habet.dev", "mergecal.habet.dev"]

    def _create_new_calendar(self) -> ICalendar:
        new_cal = ICalendar()
        new_cal.add("prodid", f"-//{self.calendar.name}//mergecal.org//")
        new_cal.add("version", "2.0")
        new_cal.add("x-wr-calname", self.calendar.name)
        self._add_timezone(new_cal)
        return new_cal

    def _add_timezone(self, cal: ICalendar) -> None:
        tzinfo = ZoneInfo(self.calendar.timezone)
        newtimezone = Timezone()
        newtimezone.add("tzid", tzinfo.key)

        now = timezone.now()
        std = TimezoneStandard()
        std.add(
            "dtstart",
            now - timedelta(days=1),
        )
        std.add("tzoffsetfrom", timedelta(seconds=-now.utcoffset().total_seconds()))
        std.add("tzoffsetto", timedelta(seconds=-now.utcoffset().total_seconds()))
        newtimezone.add_component(std)

        cal.add_component(newtimezone)

    def _add_sources(self) -> None:
        existing_uids = set()
        for source in self.calendar.calendarOf.all():
            self._add_source_events(source, existing_uids)

    def _add_source_events(self, source: Source, existing_uids: set) -> None:
        source_calendar = None
        if is_meetup_url(source.url):
            source_calendar = fetch_and_create_meetup_calendar(source.url)
        else:
            source_calendar = self._fetch_source_calendar(source)
        if source_calendar:
            for component in source_calendar.walk("VEVENT"):
                self._process_event(component, source, existing_uids)

    def _fetch_source_calendar(self, source: Source) -> None | ICalendar:
        url = source.url
        headers = {
            "User-Agent": "MergeCal/1.0 (https://mergecal.org)",
            "Accept": "text/calendar, application/calendar+xml, application/calendar+json",  # noqa: E501
            "Accept-Language": "en-US,en;q=0.9",
            "Cache-Control": "no-cache",
        }

        session = self.session

        def validate_calendar(cal: ICalendar) -> None:
            if not cal.walk():
                msg = f"Calendar from {url} contains no components"
                raise ValueError(msg)

        try:
            response = session.get(url, headers=headers, timeout=30)
            response.encoding = "utf-8"
            response.raise_for_status()

            # Log the response content for debugging
            logger.debug("Response content for %s: %s...", url, response.text[:500])

            calendar = ICalendar.from_ical(response.text)
            validate_calendar(calendar)
        except RequestException as e:
            self._add_source_error(source, f"HTTP error: {e!s}")
            return None
        except ValueError as e:
            self._add_source_error(source, f"Parsing error: {e!s}")
            return None

        return calendar

    def _process_event(self, event: Event, source: Source, existing_uids: set) -> None:
        uid = event.get("uid")
        if uid is None or uid not in existing_uids:
            self._apply_event_rules(event, source)
            self.merged_calendar.add_component(event)
            if uid is not None:
                existing_uids.add(uid)

    def _apply_event_rules(self, event: Event, source: Source) -> None:
        if self.calendar.include_source:
            event["summary"] = f"{source.name}: {event.get('summary')}"

        if self.calendar.show_branding:
            self._add_branding(event)

    def _add_branding(self, event: Event) -> None:
        branding = "\nThis event is brought to you by https://mergecal.org."
        description = event.get("description", "")
        event["description"] = description + branding

    def _add_domain_warning(self, event: Event) -> None:
        warning = (
            "You are using an outdated domain. Please update to https://mergecal.org."
        )
        description = event.get("description", "")
        event["description"] = warning + "\n" + description

    def _create_session(self) -> Session:
        session = Session()
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[500, 502, 503, 504],
        )
        session.mount("http://", HTTPAdapter(max_retries=retries))
        session.mount("https://", HTTPAdapter(max_retries=retries))
        return session

    def _add_source_error(self, source: Source, error_message: str) -> None:
        if not hasattr(self, "source_errors"):
            self.source_errors = []
        self.source_errors.append(
            {
                "source_name": source.name,
                "source_url": source.url,
                "error": error_message,
            },
        )

    def _finalize_merged_calendar(self) -> None:
        if hasattr(self, "source_errors") and self.source_errors:
            error_event = Event()
            error_event.add("summary", "MergeCal: Source Errors")
            error_description = "The following sources had errors:\n\n"
            for error in self.source_errors:
                error_description += f"- {error['source_name']} ({error['source_url']}): {error['error']}\n"  # noqa: E501
            error_event.add("description", error_description)
            error_event.add("dtstart", timezone.now())
            error_event.add("dtend", timezone.now() + timedelta(hours=1))
            self.merged_calendar.add_component(error_event)
