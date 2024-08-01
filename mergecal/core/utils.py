# core/utils.py

from django.conf import settings
from django.contrib.sites.models import Site


def get_site_url() -> str:
    """Generates the full URL of the current site based on DEBUG mode.

    Returns:
        str: The full URL of the site, including the scheme.
    """
    url_scheme = "http" if settings.DEBUG else "https"
    current_site_domain = Site.objects.get_current().domain
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
