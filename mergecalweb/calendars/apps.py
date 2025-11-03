from django.apps import AppConfig


class CalendarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecalweb.calendars"

    def ready(self):
        from mergecalweb.calendars import signals  # noqa: F401, PLC0415
