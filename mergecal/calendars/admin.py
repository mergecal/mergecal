from django.contrib import admin

from .models import Calendar, Source


class CommentInline(admin.TabularInline):
    model = Source


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "owner", "timezone", "uuid")  # Adjust the fields as needed
    search_fields = [
        "name",
        "owner__username",
    ]  # Enable search by name and owner's username
    inlines = [CommentInline]
    fieldsets = (
        (None, {"fields": ("name", "uuid", "owner", "timezone", "include_source")}),
        (
            "Advanced options",
            {
                "classes": ("collapse",),
                "fields": ("calendar_file_str",),
            },
        ),
    )
    readonly_fields = ("uuid",)  # UUID should be readonly


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "calendar")  # Adjust the fields as needed
    search_fields = [
        "name",
        "calendar__name",
    ]  # Enable search by name and calendar name
    list_filter = ("calendar",)  # Filter by calendar

    # If you want to customize form fields
    fieldsets = ((None, {"fields": ("name", "url", "calendar")}),)
