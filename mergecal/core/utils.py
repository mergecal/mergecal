# core/utils.py
import logging
import uuid
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sites.models import Site
from django.core.cache import cache

logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 3600  # 1 hour in seconds


def get_current_site_domain():
    """
    Get the current site's domain, using cache to minimize database queries.
    """
    cached_domain = cache.get("current_site_domain")
    if cached_domain is None:
        current_site = Site.objects.get_current()
        cached_domain = current_site.domain
        cache.set("current_site_domain", cached_domain, CACHE_TIMEOUT)
    return cached_domain


def get_site_url() -> str:
    """Generates the full URL of the current site based on DEBUG mode.

    Returns:
        str: The full URL of the site, including the scheme.
    """
    url_scheme = "http" if settings.DEBUG else "https"
    current_site_domain = get_current_site_domain()
    return f"{url_scheme}://{current_site_domain}"


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
    current_site_domain = get_current_site_domain()
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
