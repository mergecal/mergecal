from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from mergecalweb.calendars.services.source_service import (
    MAX_REQUEST_TIMEOUT,
    MIN_PER_SOURCE_TIMEOUT,
    SAFETY_BUFFER,
    SourceService,
)

from .factories import CalendarFactory
from .factories import SourceFactory


@pytest.mark.django_db
class TestDynamicTimeoutRedistribution:
    """Test that dynamic timeout redistribution works correctly"""

    @patch("mergecalweb.calendars.services.source_service.time.time")
    @patch("mergecalweb.calendars.services.source_processor.SourceProcessor")
    def test_timeout_increases_when_sources_are_fast(
        self,
        mock_processor_class: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        """Test that remaining time is redistributed to later sources when earlier sources are fast"""
        # Setup: Create 3 sources
        calendar = CalendarFactory()
        sources = [
            SourceFactory(calendar=calendar, url="http://example.com/cal1.ics"),
            SourceFactory(calendar=calendar, url="http://example.com/cal2.ics"),
            SourceFactory(calendar=calendar, url="http://example.com/cal3.ics"),
        ]

        # Mock time progression: each source takes 2 seconds (fast)
        # Initial time = 0, after source 1 = 2s, after source 2 = 4s, after source 3 = 6s
        mock_time.side_effect = [0.0, 0.0, 2.0, 2.0, 4.0, 4.0, 6.0]

        # Mock the processor to avoid actual calendar fetching
        mock_processor = MagicMock()
        mock_processor.source_data.ical = None
        mock_processor_class.return_value = mock_processor

        # Calculate expected timeouts
        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER  # 55 seconds

        # Source 1: (55 - 0) / 3 = 18.33 -> 18s
        expected_timeout_1 = int(available_time / 3)
        # Source 2: (55 - 2) / 2 = 26.5 -> 26s (more time!)
        expected_timeout_2 = int((available_time - 2) / 2)
        # Source 3: (55 - 4) / 1 = 51s (even more time!)
        expected_timeout_3 = int((available_time - 4) / 1)

        # Execute
        service = SourceService()
        service.process_sources(sources)

        # Verify: Check that each processor was created with increasing timeouts
        calls = mock_processor_class.call_args_list
        assert len(calls) == 3

        # Verify timeouts increase as sources complete quickly
        actual_timeout_1 = calls[0][1]["timeout"]
        actual_timeout_2 = calls[1][1]["timeout"]
        actual_timeout_3 = calls[2][1]["timeout"]

        assert actual_timeout_1 == expected_timeout_1
        assert actual_timeout_2 == expected_timeout_2
        assert actual_timeout_3 == expected_timeout_3

        # Verify redistribution: later timeouts should be higher than first
        assert actual_timeout_2 > actual_timeout_1
        assert actual_timeout_3 > actual_timeout_2

    @patch("mergecalweb.calendars.services.source_service.logger")
    @patch("mergecalweb.calendars.services.source_processor.SourceProcessor")
    def test_warning_logged_when_too_many_sources(
        self,
        mock_processor_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test that a warning is logged when there are too many sources for available time"""
        # Setup: Create sources that would require more time than available
        calendar = CalendarFactory()
        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER  # 55 seconds
        # Need more than 55s at MIN_PER_SOURCE_TIMEOUT (5s) = 12+ sources
        num_sources = (available_time // MIN_PER_SOURCE_TIMEOUT) + 2  # 13 sources

        sources = [
            SourceFactory(calendar=calendar, url=f"http://example.com/cal{i}.ics")
            for i in range(num_sources)
        ]

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.source_data.ical = None
        mock_processor_class.return_value = mock_processor

        # Execute
        service = SourceService()
        service.process_sources(sources)

        # Verify: Check that warning was logged
        warning_calls = [
            call for call in mock_logger.warning.call_args_list if len(call[0]) > 0
        ]
        assert len(warning_calls) > 0

        # Verify warning message
        warning_message = warning_calls[0][0][0]
        assert "too high" in warning_message.lower()

    @patch("mergecalweb.calendars.services.source_service.time.time")
    @patch("mergecalweb.calendars.services.source_processor.SourceProcessor")
    def test_minimum_timeout_respected(
        self,
        mock_processor_class: MagicMock,
        mock_time: MagicMock,
    ) -> None:
        """Test that timeouts never go below MIN_PER_SOURCE_TIMEOUT"""
        # Setup: Create 2 sources, simulate very slow first source
        calendar = CalendarFactory()
        sources = [
            SourceFactory(calendar=calendar, url="http://example.com/cal1.ics"),
            SourceFactory(calendar=calendar, url="http://example.com/cal2.ics"),
        ]

        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER  # 55 seconds

        # Mock time: first source takes 53 seconds (very slow!)
        # This leaves only 2 seconds for the second source
        # But it should get MIN_PER_SOURCE_TIMEOUT (5s) instead
        mock_time.side_effect = [0.0, 0.0, 53.0, 53.0]

        # Mock the processor
        mock_processor = MagicMock()
        mock_processor.source_data.ical = None
        mock_processor_class.return_value = mock_processor

        # Execute
        service = SourceService()
        service.process_sources(sources)

        # Verify: Second source should get minimum timeout
        calls = mock_processor_class.call_args_list
        timeout_for_second_source = calls[1][1]["timeout"]

        # Despite only 2s remaining, should get the minimum 5s
        assert timeout_for_second_source == MIN_PER_SOURCE_TIMEOUT
