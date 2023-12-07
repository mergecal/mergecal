from unittest.mock import patch

import requests
from django.core.exceptions import ValidationError
from django.test import TestCase
from requests.exceptions import RequestException

from mergecal.calendars.models import Calendar, Source
from mergecal.calendars.utils import (
    combine_calendar,  # Assuming combine_calendar is in utils.py
)
from mergecal.users.models import User


class BaseTest(TestCase):
    def setUp(self):
        # Common setup tasks
        self.user = User.objects.create(
            email="testuser@example.com", password="testpassword"
        )
        self.calendar = Calendar.objects.create(name="Test Calendar", owner=self.user)


class CalendarModelTest(BaseTest):
    def setUp(self):
        super().setUp()

    def test_calendar_creation(self):
        self.assertEqual(self.calendar.name, "Test Calendar")
        self.assertIsNotNone(self.calendar.uuid)

    def test_string_representation(self):
        self.assertEqual(str(self.calendar), "Test Calendar")

    def test_timezone_field(self):
        # Test the default timezone
        self.assertEqual(self.calendar.timezone, "America/New_York")

    def test_get_calendar_file_url(self):
        # Test the get_calendar_file_url method
        self.assertEqual(
            self.calendar.get_calendar_file_url(),
            f"/calendars/{self.calendar.uuid}.ical",
        )


class SourceModelTest(BaseTest):
    def setUp(self):
        super().setUp()
        self.source = Source.objects.create(
            name="Test Source",
            url="http://example.com/test.ical",
            calendar=self.calendar,
        )

    def test_source_creation(self):
        self.assertEqual(self.source.name, "Test Source")
        self.assertEqual(self.source.url, "http://example.com/test.ical")

    def test_string_representation(self):
        self.assertEqual(str(self.source), "Test Source")

    def test_url_validation_success(self):
        with patch("requests.get") as mock_get:
            mock_get.return_value.status_code = 200
            mock_get.return_value.text = "VALID ICAL DATA"
            # Attempt to save the source with a valid URL
            self.source.save()

    def test_url_validation_failure(self):
        with patch("requests.get") as mock_get:
            # Simulate a RequestException
            mock_get.side_effect = RequestException()

            # Create a new source instance to test the validation
            invalid_source = Source(
                name="Invalid Source",
                url="http://invalidurl.com/test.ical",
                calendar=self.calendar,
            )

            # Assert that ValidationError is raised
            with self.assertRaises(ValidationError):
                invalid_source.full_clean()  # Use full_clean to trigger validation

    def test_get_absolute_url(self):
        # Test the get_absolute_url method
        pass


class CombineCalendarTest(TestCase):
    def setUp(self):
        self.user = User.objects.create(
            email="testuser@example.com", password="testpassword"
        )
        self.calendar = Calendar.objects.create(
            name="Aggregated Calendar", owner=self.user
        )

        # Create mock calendar data
        self.mock_calendar_data_1 = (
            "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Event 1\nEND:VEVENT\nEND:VCALENDAR"
        )
        self.mock_calendar_data_2 = (
            "BEGIN:VCALENDAR\nBEGIN:VEVENT\nSUMMARY:Event 2\nEND:VEVENT\nEND:VCALENDAR"
        )

        # Create sources
        Source.objects.create(
            name="Source 1", url="http://example.com/cal1.ical", calendar=self.calendar
        )
        Source.objects.create(
            name="Source 2", url="http://example.com/cal2.ical", calendar=self.calendar
        )

    @patch("requests.get")
    def test_combine_calendar(self, mock_get):
        # Mock responses for each source
        mock_get.side_effect = [
            MockResponse(self.mock_calendar_data_1, 200),
            MockResponse(self.mock_calendar_data_2, 200),
        ]

        # Call the combine_calendar function
        combine_calendar(self.calendar)

        # Check if the aggregated calendar contains events from both sources
        self.assertIn("Event 1", self.calendar.calendar_file_str)
        self.assertIn("Event 2", self.calendar.calendar_file_str)


class MockResponse:
    def __init__(self, text, status_code):
        self.text = text
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code != 200:
            raise requests.HTTPError()
