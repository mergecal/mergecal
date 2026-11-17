from __future__ import annotations

from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from django.http import HttpRequest

OFFICIAL_HOSTS = {"mergecal.org", "www.mergecal.org"}


def nav_base_url(request: HttpRequest) -> dict[str, str]:
    if settings.DEBUG or request.get_host().lower() in OFFICIAL_HOSTS:
        return {"nav_base_url": ""}
    return {"nav_base_url": "https://mergecal.org"}
