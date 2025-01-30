import pytest
from django.urls import resolve
from django.urls import reverse

from mergecalweb.calendars import views
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source


@pytest.mark.django_db
class TestCalendarUrls:
    """Test suite for calendar URL patterns."""

    def test_calendar_list_url(self) -> None:
        """Test calendar list URL pattern."""
        url = reverse("calendars:calendar_list")
        assert url == "/calendars/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.UserCalendarListView

    def test_calendar_create_url(self) -> None:
        """Test calendar creation URL pattern."""
        url = reverse("calendars:calendar_create")
        assert url == "/calendars/create/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.CalendarCreateView

    def test_calendar_update_url(self, calendar: Calendar) -> None:
        """Test calendar update URL pattern."""
        url = reverse("calendars:calendar_update", kwargs={"uuid": calendar.uuid})
        assert url == f"/calendars/{calendar.uuid}/update/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.CalendarUpdateView

    def test_calendar_delete_url(self, calendar: Calendar) -> None:
        """Test calendar deletion URL pattern."""
        url = reverse("calendars:calendar_delete", kwargs={"uuid": calendar.uuid})
        assert url == f"/calendars/{calendar.uuid}/delete/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.CalendarDeleteView

    def test_calendar_file_urls(self, calendar: Calendar) -> None:
        """Test calendar file URL patterns."""
        # Test .ical extension
        url = reverse("calendars:calendar_file", kwargs={"uuid": calendar.uuid})
        assert url == f"/calendars/{calendar.uuid}.ical"
        resolver = resolve(url)
        assert resolver.func.view_class == views.CalendarFileAPIView

        # Test .ics extension
        url = reverse("calendars:calendar_file_ics", kwargs={"uuid": calendar.uuid})
        assert url == f"/calendars/{calendar.uuid}.ics"
        resolver = resolve(url)
        assert resolver.func.view_class == views.CalendarFileAPIView

    def test_source_urls(self, calendar: Calendar, source: Source) -> None:
        """Test source-related URL patterns."""
        # Add source
        url = reverse("calendars:source_add", kwargs={"uuid": calendar.uuid})
        assert url == f"/calendars/calendar/{calendar.uuid}/source/add/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.SourceAddView

        # Edit source
        url = reverse("calendars:source_edit", kwargs={"pk": source.pk})
        assert url == f"/calendars/source/{source.pk}/edit/"
        resolver = resolve(url)
        assert resolver.func.view_class == views.SourceEditView

        # Delete source
        url = reverse("calendars:source_delete", kwargs={"pk": source.pk})
        assert url == f"/calendars/source/{source.pk}/delete/"
        resolver = resolve(url)
        assert resolver.func == views.source_delete


@pytest.mark.django_db
class TestCalendarViewNames:
    """Test suite for view name resolution."""

    def test_view_names(self, calendar: Calendar, source: Source) -> None:
        """Test all view names resolve correctly."""
        views = [
            ("calendars:calendar_list", {}),
            ("calendars:calendar_create", {}),
            ("calendars:calendar_update", {"uuid": calendar.uuid}),
            ("calendars:calendar_delete", {"uuid": calendar.uuid}),
            ("calendars:calendar_file", {"uuid": calendar.uuid}),
            ("calendars:calendar_file_ics", {"uuid": calendar.uuid}),
            ("calendars:source_add", {"uuid": calendar.uuid}),
            ("calendars:source_edit", {"pk": source.pk}),
            ("calendars:source_delete", {"pk": source.pk}),
        ]

        for view_name, kwargs in views:
            url = reverse(view_name, kwargs=kwargs)
            assert url  # URL resolves without error

            # Basic sanity check that all URLs start with /calendars/
            assert url.startswith("/calendars/")
