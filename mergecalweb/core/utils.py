# core/utils.py
import logging
import uuid
from urllib.parse import urlparse

from django.conf import settings

logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 3600  # 1 hour in seconds
CANONICAL_SITE_URL = "https://mergecal.org"
LOCAL_SITE_URL = "http://localhost:8000"


def get_site_url() -> str:
    if settings.DEBUG:
        return LOCAL_SITE_URL
    return CANONICAL_SITE_URL


def get_stripe_dashboard_url(account_id: str = "") -> str:
    """Generates the URL of the Stripe dashboard for the current user.

    Returns:
        str: The URL of the Stripe dashboard for the current user.
    """
    live_mode = settings.STRIPE_LIVE_MODE
    if account_id == "":
        return f"https://dashboard.stripe.com{'/test' if not live_mode else ''}"

    return (
        f"https://dashboard.stripe.com/{account_id}{'/test' if not live_mode else ''}"
    )


def is_local_url(url: str) -> bool:
    """
    Check if the given URL is from the current site.

    Args:
    url (str): The URL to check.

    Returns:
    bool: True if the URL is from the current site, False otherwise.
    """
    current_site_domain = urlparse(get_site_url()).netloc

    parsed_url = urlparse(url)
    url_domain = parsed_url.netloc

    # Remove 'www.' from both domains for comparison
    current_site_domain = current_site_domain.removeprefix("www.")
    url_domain = url_domain.removeprefix("www.")
    return url_domain == current_site_domain


TWO = 2


def parse_calendar_uuid(url: str) -> uuid.UUID | None:
    """
    Parse and return the UUID from a MergeCal calendar URL.

    Args:
    url (str): The URL to parse.

    Returns:
    uuid.UUID | None: The UUID object if found and valid, None otherwise.
    """
    parsed_url = urlparse(url)
    path = parsed_url.path.strip("/")
    parts = path.split("/")

    if len(parts) == TWO and parts[0] == "calendars":
        calendar_id = parts[1].split(".")[0]  # Remove file extension
        try:
            return uuid.UUID(calendar_id)
        except ValueError:
            return None

    return None
