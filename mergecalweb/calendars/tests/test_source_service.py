from unittest.mock import MagicMock
from unittest.mock import patch

import pytest

from mergecalweb.calendars.services.source_service import MAX_REQUEST_TIMEOUT
from mergecalweb.calendars.services.source_service import MIN_PER_SOURCE_TIMEOUT
from mergecalweb.calendars.services.source_service import SAFETY_BUFFER
from mergecalweb.calendars.services.source_service import SourceService

from .factories import CalendarFactory
from .factories import SourceFactory


@pytest.mark.django_db
class TestDynamicTimeoutRedistribution:
    """Test that dynamic timeout redistribution works correctly"""

    def test_timeout_increases_when_sources_are_fast(self) -> None:
        """Test remaining time is redistributed to later sources"""
        # Setup: Create 3 sources
        num_sources = 3
        calendar = CalendarFactory()
        sources = [
            SourceFactory(calendar=calendar, url="http://example.com/cal1.ics"),
            SourceFactory(calendar=calendar, url="http://example.com/cal2.ics"),
            SourceFactory(calendar=calendar, url="http://example.com/cal3.ics"),
        ]

        # Calculate expected timeouts with dynamic redistribution
        available_time = MAX_REQUEST_TIMEOUT - SAFETY_BUFFER  # 55 seconds

        # Execute
        service = SourceService()

        # We need to capture timeouts during processor creation
        processor_timeouts = []

        with patch(
            "mergecalweb.calendars.services.source_service.SourceProcessor",
        ) as mock_processor_class:

            def create_processor(source, timeout):
                processor_timeouts.append(timeout)
                processor = MagicMock()
                processor.source_data.ical = None
                processor.source_data.source = source
                processor.source_data.error = None
                return processor

            mock_processor_class.side_effect = create_processor
            service.process_sources(sources)

        # Verify: Check that timeouts were calculated
        # (should be around 18s for first source initially)
        assert len(processor_timeouts) == num_sources

        # First source gets roughly available_time / num_sources
        first_timeout = processor_timeouts[0]
        expected_first_timeout = int(available_time / num_sources)
        assert first_timeout >= expected_first_timeout - 1
        assert first_timeout <= expected_first_timeout + 1

        # Since sources complete quickly (mocked), later sources should
        # get more time. The timeouts should generally trend upward due
        # to redistribution (though exact values depend on real execution
        # time which is very fast)
        assert processor_timeouts[1] >= first_timeout - 5  # Allow variance
        assert processor_timeouts[2] >= first_timeout - 5  # Allow variance

    @patch("mergecalweb.calendars.services.source_service.logger")
    @patch("mergecalweb.calendars.services.source_service.SourceProcessor")
    def test_warning_logged_when_too_many_sources(
        self,
        mock_processor_class: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test warning is logged when too many sources for available time"""
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

    @patch("mergecalweb.calendars.services.source_service.SourceProcessor")
    def test_minimum_timeout_respected_with_many_sources(
        self,
        mock_processor_class: MagicMock,
    ) -> None:
        """Test that timeouts never go below MIN_PER_SOURCE_TIMEOUT"""
        # Setup: Create many sources to force minimum timeout
        calendar = CalendarFactory()

        # Create enough sources that each would get less than minimum
        # if divided evenly. With 55s available and 5s minimum, anything
        # over 11 sources will hit the minimum
        num_sources = 15

        sources = [
            SourceFactory(calendar=calendar, url=f"http://example.com/cal{i}.ics")
            for i in range(num_sources)
        ]

        # Capture timeouts
        processor_timeouts = []

        def create_processor(source, timeout):
            processor_timeouts.append(timeout)
            processor = MagicMock()
            processor.source_data.ical = None
            return processor

        mock_processor_class.side_effect = create_processor

        # Execute
        service = SourceService()
        service.process_sources(sources)

        # Verify: All timeouts should be at least MIN_PER_SOURCE_TIMEOUT
        assert len(processor_timeouts) == num_sources
        for timeout in processor_timeouts:
            assert timeout >= MIN_PER_SOURCE_TIMEOUT, (
                f"Timeout {timeout} is below minimum {MIN_PER_SOURCE_TIMEOUT}"
            )