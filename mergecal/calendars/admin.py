from django.contrib import admin
from django.db.models import Count
from django.utils.html import format_html

from .models import Calendar
from .models import Source


class CommentInline(admin.TabularInline):
    model = Source


@admin.register(Calendar)
class CalendarAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "owner_email",
        "timezone",
        "uuid_link",
        "source_count",
        "created",
        "modified",
    )

    search_fields = [
        "name",
        "uuid",
        "owner__username",
        "owner__email",
    ]

    inlines = [CommentInline]

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "name",
                    "uuid",
                    "owner",
                    "timezone",
                    "include_source",
                    "created",
                    "modified",
                ),
            },
        ),
        ("customization", {"fields": ("update_frequency_seconds", "remove_branding")}),
    )
    readonly_fields = ("uuid", "created", "modified")

    @admin.display(ordering="source_count")
    def source_count(self, obj):
        return obj.source_count

    @admin.display(
        description="Owner Email",
        ordering="owner__email",
    )
    def owner_email(self, obj):
        return obj.owner.email if obj.owner else None

    def get_queryset(self, request):
        queryset = super().get_queryset(request).prefetch_related("owner")
        return queryset.annotate(source_count=Count("calendarOf"))

    @admin.display(description="UUID")
    def uuid_link(self, obj):
        url = obj.get_calendar_view_url()
        return format_html('<a href="{}">{}</a>', url, obj.uuid)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "url",
        "calendar",
        "include_title",
        "include_description",
        "include_location",
        "custom_prefix",
    )
    search_fields = ["name", "calendar__name", "url"]
    list_filter = (
        "calendar",
        "include_title",
        "include_description",
        "include_location",
    )

    fieldsets = (
        (None, {"fields": ("name", "url", "calendar")}),
        (
            "Customization",
            {
                "fields": (
                    "include_title",
                    "include_description",
                    "include_location",
                    "custom_prefix",
                    "exclude_keywords",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("created", "modified")}),
    )

    readonly_fields = ("created", "modified")
