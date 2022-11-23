from django.urls import path

from .views import (
    create_calendar_form,
    create_source_form,
    delete_calendar,
    delete_source,
    detail_calendar,
    detail_source,
    manage_calendar,
    manage_source,
    update_calendar,
    update_source,
)

app_name = "calendars"

urlpatterns = [
    path("", manage_calendar, name="manage-calendar"),
    path("htmx/calendar/<pk>/", detail_calendar, name="detail-calendar"),
    path("htmx/calendar/<pk>/update/", update_calendar, name="update-calendar"),
    path("htmx/calendar/<pk>/delete/", delete_calendar, name="delete-calendar"),
    path(
        "htmx/create-calendar-form/", create_calendar_form, name="create-calendar-form"
    ),
    path("<pk>/", manage_source, name="manage-source"),
    path("htmx/source/<pk>/", detail_source, name="detail-source"),
    path("htmx/source/<pk>/update/", update_source, name="update-source"),
    path("htmx/source/<pk>/delete/", delete_source, name="delete-source"),
    path(
        "<pk>/htmx/create-source-form/", create_source_form, name="create-source-form"
    ),
]
