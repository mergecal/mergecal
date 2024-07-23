from django.apps import AppConfig


class CalendarsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mergecal.calendars"

    def ready(self):
        # Import the signal handlers to ensure they're registered
        pass
