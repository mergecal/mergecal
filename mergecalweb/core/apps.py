import os

from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecalweb.core"

    def ready(self):
        if os.environ.get("DJANGO_SETTINGS_MODULE") == "config.settings.production":
            import posthog  # noqa: PLC0415

            posthog.api_key = settings.POSTHOG_API_KEY
            posthog.host = "https://m.mergecal.org"
