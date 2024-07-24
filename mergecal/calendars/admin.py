from django.contrib import admin
from django.utils.html import format_html

from .models import Calendar
from .models import Source


class CommentInline(admin.TabularInline):
    model = Source


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = ("name", "owner_email", "timezone", "uuid_link")

    search_fields = [
        "name",
        "uuid",
        "owner__username",
        "owner__email",
    ]

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
    readonly_fields = ("uuid",)

    @admin.display(
        description="Owner Email",
        ordering="owner__email",
    )
    def owner_email(self, obj):
        return obj.owner.email if obj.owner else None

    @admin.display(description="UUID")
    def uuid_link(self, obj):
        url = obj.get_calendar_view_url()
        return format_html('<a href="{}">{}</a>', url, obj.uuid)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = ("name", "url", "calendar")  # Adjust the fields as needed
    search_fields = [
        "name",
        "calendar__name",
        "url",
    ]  # Enable search by name and calendar name
    list_filter = ("calendar",)

    fieldsets = ((None, {"fields": ("name", "url", "calendar")}),)
