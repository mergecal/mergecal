import logging
from datetime import timedelta

import sentry_sdk
import x_wr_timezone
from django.core.cache import cache
from django.http import HttpRequest
from django.utils import timezone
from icalendar import Alarm
from icalendar import Calendar as ICalendar
from icalendar import Event
from requests import RequestException
from requests import Session
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from mergecalweb.calendars.calendar_fetcher import CalendarFetcher
from mergecalweb.calendars.meetup import fetch_and_create_meetup_calendar
from mergecalweb.calendars.meetup import is_meetup_url
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.core.utils import is_local_url
from mergecalweb.core.utils import parse_calendar_uuid

logger = logging.getLogger(__name__)


class CalendarMergerService:
    # TODO: remove request - pass in request domain instead
    def __init__(self, calendar: Calendar, request: HttpRequest):
        self.calendar = calendar
        self.request = request
        self.user = calendar.owner
        self.calendar_fetcher = CalendarFetcher()
        self.is_outdated_domain = self._check_outdated_domain()
        self.merged_calendar = None
        self.existing_tzids = set()

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
            self._check_for_free_account()
            calendar_str = self.merged_calendar.to_ical().decode("utf-8")

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
        return origin_domain in ["calmerge.habet.dev", "mergecalweb.habet.dev"]

    def _create_new_calendar(self) -> ICalendar:
        new_cal = ICalendar()
        new_cal.add("prodid", f"-//{self.calendar.name}//mergecal.org//")
        new_cal.add("version", "2.0")
        new_cal.add("x-wr-calname", self.calendar.name)
        return new_cal

    def _add_sources(self) -> None:
        existing_uids = set()
        source_calendars = []
        for source in self.calendar.calendarOf.all():
            if not is_local_url(source.url):
                source_calendars.append(source)
                continue

            # if it's a local URL, we need to fetch the calendar sorurce
            logger.info("Local URL detected: %s", source.url)
            uuid = parse_calendar_uuid(source.url)
            if uuid and uuid != self.calendar.uuid:  # avoid recursive hell
                try:
                    sub_calendar = Calendar.objects.get(uuid=uuid)
                    source_calendars.extend(sub_calendar.calendarOf.all())
                except Calendar.DoesNotExist:
                    logger.warning("Calendar not found for UUID: %s", uuid)

        for source in source_calendars:
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

            for component in source_calendar.walk("VTIMEZONE"):
                tzid = component.get("tzid")
                if tzid in self.existing_tzids:
                    continue
                self.existing_tzids.add(tzid)
                self.merged_calendar.add_component(component)

    def _fetch_source_calendar(self, source: Source) -> None | ICalendar:
        def validate_calendar(cal: ICalendar) -> None:
            if not cal.walk():
                msg = f"Calendar from {url} contains no components"
                raise ValueError(msg)

        url = source.url
        calendar_data = self.calendar_fetcher.fetch_calendar(url)

        try:
            calendar = ICalendar.from_ical(calendar_data)
            validate_calendar(calendar)
            return x_wr_timezone.to_standard(calendar)
        except RequestException as e:
            error_message = f"HTTP error: {e!s}"
            logger.warning(error_message)
            self._add_source_error(source, error_message)
            return None
        except ValueError as e:
            error_message = f"Error parsing calendar: {e!s}"
            logger.warning(error_message)
            self._add_source_error(source, error_message)
            return None

    def _process_event(self, event: Event, source: Source, existing_uids: set) -> None:
        uid = event.get("uid")
        if uid is None or uid not in existing_uids:
            self._apply_event_rules(event, source)
            if self._should_include_event(event, source):
                self.merged_calendar.add_component(event)
                if uid is not None:
                    existing_uids.add(uid)

    def _apply_event_rules(self, event: Event, source: Source) -> None:
        if self.calendar.owner.can_customize_sources:
            if not source.include_title:
                event["summary"] = source.custom_prefix or source.name
            elif source.custom_prefix:
                event["summary"] = f"{source.custom_prefix}: {event.get('summary')}"

            if not source.include_description:
                event.pop("description", None)

            if not source.include_location:
                event.pop("location", None)

        if self.calendar.show_branding:
            self._add_branding(event)

    def _should_include_event(self, event: Event, source: Source) -> bool:
        if not self.calendar.owner.can_customize_sources or not source.exclude_keywords:
            return True

        exclude_keywords = [
            kw.strip().lower() for kw in source.exclude_keywords.split(",")
        ]
        event_title = event.get("summary", "").lower()
        return not any(kw in event_title for kw in exclude_keywords)

    def _add_branding(self, event: Event) -> None:
        branding = "\n\nThis event is powered by MergeCal \nhttps://mergecal.org"
        description = event.get("description", "")
        event["description"] = description + branding
        summary = event.get("summary", "")
        event["summary"] = summary + " (via MergeCal.org)"

    def _add_domain_warning(self, event: Event) -> None:
        warning = (
            "You are using an outdated domain. Please update to https://mergecal.org"
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

    def _check_for_free_account(self) -> None:
        user = self.calendar.owner
        if not user.is_free_tier:
            return

        logger.warning(
            "User %s (Free Tier) is downloading calendar %s",
            self.request.user,
            self.calendar.uuid,
        )
        warning_event = self._create_access_warning_event()
        if warning_event and self.merged_calendar:
            self.merged_calendar.add_component(warning_event)

        scope = sentry_sdk.get_current_scope()
        scope.set_tag("tier", "free")
        scope.set_user({"id": user.pk, "email": user.email})
        scope.set_extra("calendar_uuid", self.calendar.uuid)
        scope.set_extra("calendar_name", self.calendar.name)
        sentry_sdk.capture_message(
            "Free account detected",
            level="warning",
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

    def _create_access_warning_event(self) -> Event:
        """Creates a warning event for users who need to subscribe."""
        warning_event = Event()

        # Set event time to today
        start_time = timezone.now()

        warning_event.add(
            "summary",
            "⚠️ Action Required: Your MergeCal Access Will Be Discontinued",
        )
        description = (
            "⚠️ Your MergeCal calendar access will be discontinued soon.\n\n"
            "🎁 Get 1 Month FREE on our Business Plan with code: FREEMONTH\n\n"
            "Subscribe now to keep your calendars synchronized:\n"
            "https://mergecal.org/pricing/"
        )

        warning_event.add("description", description)
        warning_event.add("dtstart", start_time)
        warning_event.add("dtend", start_time + timedelta(hours=24))
        warning_event.add("priority", 1)  # High priority
        warning_event.add("uid", f"access-warning-{self.calendar.uuid}")

        # Add alarm to trigger 3 hours from now
        alarm = Alarm()
        alarm.add("action", "DISPLAY")
        alarm.add(
            "description",
            "Your MergeCal access will be discontinued. Subscribe to our Business Plan - 1 Month FREE with code: FREEMONTH",  # noqa: E501
        )
        alarm.add("trigger", timedelta(hours=3))  # Notify in 3 hours
        warning_event.add_component(alarm)

        return warning_event
