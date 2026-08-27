from django.apps import AppConfig
from django.conf import settings


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecalweb.core"

    def ready(self):
        # A blank key means no project to send to, which is the normal state
        # for local and test runs. Capture calls no-op in that case.
        if settings.POSTHOG_API_KEY:
            import posthog  # noqa: PLC0415

            posthog.api_key = settings.POSTHOG_API_KEY
            posthog.host = settings.POSTHOG_HOST
