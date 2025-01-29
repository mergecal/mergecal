from django.urls import path

from mergecalweb.calendars.views import CalendarCreateView
from mergecalweb.calendars.views import CalendarDeleteView
from mergecalweb.calendars.views import CalendarFileAPIView
from mergecalweb.calendars.views import CalendarUpdateView
from mergecalweb.calendars.views import SourceAddView
from mergecalweb.calendars.views import SourceEditView
from mergecalweb.calendars.views import UserCalendarListView
from mergecalweb.calendars.views import calendar_iframe
from mergecalweb.calendars.views import calendar_view
from mergecalweb.calendars.views import source_delete

app_name = "calendars"

urlpatterns = [
    path("", UserCalendarListView.as_view(), name="calendar_list"),
    path("create/", CalendarCreateView.as_view(), name="calendar_create"),
    path("<uuid:uuid>/update/", CalendarUpdateView.as_view(), name="calendar_update"),
    path("<uuid:uuid>/delete/", CalendarDeleteView.as_view(), name="calendar_delete"),
    path("source/<int:pk>/edit/", SourceEditView.as_view(), name="source_edit"),
    path(
        "calendar/<uuid:uuid>/source/add/",
        SourceAddView.as_view(),
        name="source_add",
    ),
    path("source/<int:pk>/delete/", source_delete, name="source_delete"),
    path("<uuid>.ical", CalendarFileAPIView.as_view(), name="calendar_file"),
    path("<uuid>.ics", CalendarFileAPIView.as_view(), name="calendar_file_ics"),
    path("<uuid>/calendar/", calendar_view, name="calendar_view"),
    path("iframe/<uuid>/", calendar_iframe, name="calendar_iframe"),
]
