from django.contrib import admin

from .models import GoogleCalendarSync


@admin.register(GoogleCalendarSync)
class GoogleCalnedarSyncAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "created",
        "google_calendar_id",
        "last_synced",
        "modified",
        "calendar",
    )
    list_filter = ("created", "modified", "calendar", "last_synced")
