from django.urls import path
from django.views.generic import TemplateView

from .views import CalendarFileAPIView
from .views import calendar_view
from .views import create_calendar_form
from .views import create_source_form
from .views import delete_calendar
from .views import delete_source
from .views import detail_calendar
from .views import detail_source
from .views import manage_calendar
from .views import manage_source
from .views import toggle_include_source
from .views import update_calendar
from .views import update_source

app_name = "calendars"

urlpatterns = [
    path("", manage_calendar, name="manage-calendar"),
    path(
        "instructions/",
        TemplateView.as_view(template_name="calendars/instructions.html"),
        name="instructions",
    ),
    path("htmx/calendar/<pk>/", detail_calendar, name="detail-calendar"),
    path("htmx/calendar/<pk>/update/", update_calendar, name="update-calendar"),
    path("htmx/calendar/<pk>/delete/", delete_calendar, name="delete-calendar"),
    path(
        "htmx/create-calendar-form/",
        create_calendar_form,
        name="create-calendar-form",
    ),
    path("<pk>/", manage_source, name="manage-source"),
    path("htmx/source/<pk>/", detail_source, name="detail-source"),
    path("htmx/source/<pk>/update/", update_source, name="update-source"),
    path("htmx/source/<pk>/delete/", delete_source, name="delete-source"),
    path(
        "<pk>/htmx/create-source-form/",
        create_source_form,
        name="create-source-form",
    ),
    path("<uuid>.ical", CalendarFileAPIView.as_view(), name="calendar_file"),
    path("<uuid>.ics", CalendarFileAPIView.as_view(), name="calendar_file_ics"),
    path("<uuid>/calendar/", calendar_view, name="calendar-view"),
    path("<uuid>/toggle-include/", toggle_include_source, name="toggle-include"),
]
