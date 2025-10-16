# ruff: noqa: E501 ERA001
import logging
import typing
import uuid
import zoneinfo

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from icalendar import Calendar as Ical
from requests.exceptions import RequestException

from mergecalweb.calendars.calendar_fetcher import CalendarFetcher
from mergecalweb.core.constants import SourceLimits
from mergecalweb.core.models import TimeStampedModel
from mergecalweb.core.utils import get_site_url
from mergecalweb.core.utils import is_local_url
from mergecalweb.core.utils import parse_calendar_uuid

if typing.TYPE_CHECKING:
    from mergecalweb.users.models import User

logger = logging.getLogger(__name__)

TWELVE_HOURS_IN_SECONDS = 43200


def validate_ical_url(url):
    logger.debug("Validating iCal URL: %s", url)

    if is_local_url(url):
        calendar_uuid = parse_calendar_uuid(url)
        if calendar_uuid:
            if not Calendar.objects.filter(uuid=calendar_uuid).exists():
                msg = "The specified MergeCal calendar does not exist."
                logger.warning(
                    "Validation failed: Local calendar not found - uuid=%s, url=%s",
                    calendar_uuid,
                    url,
                )
                raise ValidationError(msg)
            logger.debug(
                "Local calendar URL validated successfully: uuid=%s",
                calendar_uuid,
            )
            return  # URL is valid, exit the function

    # if url is meetup.com, skip validation
    if "meetup.com" in url:
        logger.debug("Skipping validation for Meetup URL: %s", url)
        return

    try:
        fetcher = CalendarFetcher()
        # Use shorter timeout for validation to prevent long form submission delays
        # 10 seconds should be enough to validate most calendar feeds
        response = fetcher.fetch_calendar(url, timeout=10)
        cal = Ical.from_ical(response)  # noqa: F841
        logger.info("iCal URL validation successful: %s", url)
    except RequestException as err:
        msg = f"Enter a valid URL. Details: {err}"
        logger.exception(
            "iCal URL validation failed (network error): url=%s",
            url,
        )
        raise ValidationError(msg) from err
    except ValueError as err:
        msg = f"Enter a valid iCalendar feed. Details: {err}"
        logger.exception(
            "iCal URL validation failed (invalid format): url=%s",
            url,
        )
        raise ValidationError(msg) from err


class Calendar(TimeStampedModel):
    name = models.CharField(max_length=255)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, db_index=True)
    owner: "User" = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
    )
    # https://stackoverflow.com/a/70251235
    TIMEZONE_CHOICES = tuple(
        (x, x)
        for x in sorted(zoneinfo.available_timezones(), key=str.lower)
        if x != "localtime"  # Exclude 'localtime' from the choices
    )

    timezone = models.CharField(
        "Timezone",
        choices=TIMEZONE_CHOICES,
        max_length=250,
        default="America/New_York",
    )

    include_source = models.BooleanField(
        default=False,
        help_text="Include source name in event title",
    )
    update_frequency_seconds = models.PositiveIntegerField(
        _("Update Frequency"),
        default=TWELVE_HOURS_IN_SECONDS,  # 12 hours in seconds
        help_text=_(
            "How often the calendar updates in seconds. "
            "Default is every 12 hours (43200 seconds).",
        ),
    )
    remove_branding = models.BooleanField(
        _("Remove MergeCal Branding"),
        default=False,
        help_text=_(
            "Remove MergeCal branding from the calendar. "
            "Only available for Business tier and above.",
        ),
    )

    class Meta(TimeStampedModel.Meta):
        ordering = ["-pk"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:calendar_update", kwargs={"uuid": self.uuid})

    def clean(self):
        logger.debug(
            "Validating calendar: name=%s, owner=%s, tier=%s, is_new=%s",
            self.name,
            self.owner.username,
            self.owner.subscription_tier,
            not self.pk,
        )

        if (
            not self.owner.can_set_update_frequency
            and self.update_frequency_seconds != TWELVE_HOURS_IN_SECONDS
        ):
            logger.warning(
                "Calendar validation failed: User %s (tier=%s) attempted to set custom update frequency",
                self.owner.username,
                self.owner.subscription_tier,
            )
            raise ValidationError(
                {
                    "update_frequency_seconds": _(
                        "You don't have permission to change the update frequency.",
                    ),
                },
            )

        if not self.owner.can_remove_branding and self.remove_branding:
            logger.warning(
                "Calendar validation failed: User %s (tier=%s) attempted to remove branding",
                self.owner.username,
                self.owner.subscription_tier,
            )
            raise ValidationError(
                {"remove_branding": _("You don't have permission to remove branding.")},
            )

        if not self.pk:  # Only check on creation, not update
            if not self.owner.can_add_calendar:
                current_count = self.owner.calendar_set.count()
                logger.warning(
                    "Calendar creation denied: User %s (tier=%s) at limit - current=%d",
                    self.owner.username,
                    self.owner.subscription_tier,
                    current_count,
                )
                msg = "Upgrade to create more calendars."
                raise ValidationError(msg)

        logger.debug("Calendar validation successful: name=%s", self.name)

    @property
    def update_frequency_hours(self):
        return self.update_frequency_seconds // 3600

    @update_frequency_hours.setter
    def update_frequency_hours(self, hours):
        self.update_frequency_seconds = hours * 3600

    @property
    def effective_update_frequency(self):
        if self.owner.can_set_update_frequency:
            return self.update_frequency_seconds
        return TWELVE_HOURS_IN_SECONDS

    @property
    def show_branding(self):
        return not (self.remove_branding and self.owner.can_remove_branding)

    def get_calendar_file_url(self):
        return reverse("calendars:calendar_file", kwargs={"uuid": self.uuid})

    def get_calendar_view_url(self):
        return reverse("calendars:calendar_view", kwargs={"uuid": self.uuid})

    def get_validator_url(self):
        """
        Generate URL for the validator page with this calendar and all its sources.
        MergeCal URL is added first, followed by all source URLs.
        """
        from urllib.parse import urlencode

        domain_name = get_site_url()
        # Start with the merged calendar URL
        urls = [f"{domain_name}{self.get_calendar_file_url()}"]

        # Add all source URLs
        urls.extend(source.url for source in self.calendarOf.all())

        # Build query string with urls[] parameters
        query_params = [("urls[]", url) for url in urls]
        query_string = urlencode(query_params)

        return f"{reverse('url_validator')}?{query_string}"

    def get_calendar_iframe(self):
        domain_name = get_site_url()
        iframe_url = reverse("calendars:calendar_iframe", kwargs={"uuid": self.uuid})
        return f'<iframe src="{domain_name}{iframe_url}" width="100%" height="600" style="border: 1px solid #ccc;" title="MergeCal Embedded Calendar"></iframe>'

    @property
    def can_add_source(self):
        user_event_count = self.calendarOf.count()
        match self.owner.subscription_tier:
            case self.owner.SubscriptionTier.FREE:
                return user_event_count < SourceLimits.FREE
            case self.owner.SubscriptionTier.PERSONAL:
                return user_event_count < SourceLimits.PERSONAL
            case self.owner.SubscriptionTier.BUSINESS:
                return user_event_count < SourceLimits.BUSINESS
            case self.owner.SubscriptionTier.SUPPORTER:
                return True


class Source(TimeStampedModel):
    name = models.CharField(
        max_length=255,
        verbose_name="Feed Name",
        help_text="A friendly name to identify this calendar feed.",
    )
    url = models.URLField(
        max_length=400,
        validators=[validate_ical_url],
        verbose_name="Feed URL",
        help_text="The URL of the iCal feed for this calendar source.",
    )
    calendar = models.ForeignKey(
        "calendars.Calendar",
        on_delete=models.CASCADE,
        related_name="calendarOf",
        verbose_name="Merged Calendar",
        help_text="The merged calendar this feed belongs to.",
    )
    include_title = models.BooleanField(
        default=True,
        verbose_name="Include Event Title",
        help_text="If checked, the original event title from this feed will be included in the merged calendar.",
    )
    include_description = models.BooleanField(
        default=True,
        verbose_name="Include Event Description",
        help_text="If checked, the event description from this feed will be included in the merged calendar.",
    )
    include_location = models.BooleanField(
        default=True,
        verbose_name="Include Event Location",
        help_text="If checked, the event location from this feed will be included in the merged calendar.",
    )
    custom_prefix = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Custom Prefix",
        help_text="Optional prefix to add before each event title from this feed (e.g., '[Work]').",
    )
    exclude_keywords = models.TextField(
        blank=True,
        verbose_name="Exclude Keywords",
        help_text="Enter keywords separated by commas. Events from this feed containing these keywords in their title will be excluded from the merged calendar.",
    )

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("calendars:source_edit", kwargs={"pk": self.pk})

    def clean(self):
        logger.debug(
            "Validating source: name=%s, url=%s, calendar=%s, owner=%s, tier=%s, is_new=%s",
            self.name,
            self.url,
            self.calendar.name,
            self.calendar.owner.username,
            self.calendar.owner.subscription_tier,
            not self.pk,
        )

        if not self.pk:  # Only check on creation, not update
            if not self.calendar.can_add_source:
                current_count = self.calendar.calendarOf.count()
                logger.warning(
                    "Source creation denied: Calendar '%s' (owner=%s, tier=%s) at limit - current=%d",
                    self.calendar.name,
                    self.calendar.owner.username,
                    self.calendar.owner.subscription_tier,
                    current_count,
                )
                msg = "upgrade to add more sources"
                raise ValidationError(msg)

        if not self.calendar.owner.can_customize_sources:
            if (
                not self.include_title
                or not self.include_description
                or not self.include_location
                or self.custom_prefix
                or self.exclude_keywords
            ):
                logger.warning(
                    "Source customization denied: User %s (tier=%s) attempted to use premium features",
                    self.calendar.owner.username,
                    self.calendar.owner.subscription_tier,
                )
                msg = "Customization features are only available for Business and Supporter plans"
                raise ValidationError(msg)

        logger.debug(
            "Source validation successful: name=%s, url=%s",
            self.name,
            self.url,
        )
