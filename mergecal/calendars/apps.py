from django.apps import AppConfig


class CalendarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecal.calendars"

    def ready(self):
        from mergecal.calendars import signals  # noqa: F401
