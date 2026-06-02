"""Tests for the optional per-source timeout override threaded through the
merge services (used by the background prefetch job)."""

from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService
from mergecalweb.calendars.services.source_processor import SourceProcessor
from mergecalweb.calendars.services.source_service import SourceService

from .factories import SourceFactory

if TYPE_CHECKING:
    from mergecalweb.calendars.models import Calendar

OVERRIDE_TIMEOUT = 45


@pytest.mark.django_db
def test_override_bypasses_budget_calculation(
    calendar: "Calendar",
    mock_calendar_request: None,
) -> None:
    """With an override, the Gunicorn-budget calculation is skipped and the
    override is handed to each SourceProcessor."""
    source = SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    service = SourceService(source_timeout=OVERRIDE_TIMEOUT)

    with (
        patch.object(SourceService, "_calculate_per_source_timeout") as calc,
        patch(
            "mergecalweb.calendars.services.source_service.SourceProcessor",
            wraps=SourceProcessor,
        ) as proc,
    ):
        service.process_sources([source])

    calc.assert_not_called()
    assert proc.call_args.kwargs["timeout"] == OVERRIDE_TIMEOUT


@pytest.mark.django_db
def test_without_override_uses_budget_calculation(
    calendar: "Calendar",
    mock_calendar_request: None,
) -> None:
    """Without an override, behavior is unchanged: the budget split is used."""
    source = SourceFactory(url="http://example.com/basic.ics", calendar=calendar)
    service = SourceService()

    with patch.object(
        SourceService,
        "_calculate_per_source_timeout",
        return_value=5,
    ) as calc:
        service.process_sources([source])

    calc.assert_called_once_with(1)


@pytest.mark.django_db
def test_merger_threads_timeout_to_fetcher(
    calendar: "Calendar",
    mock_calendar_request: None,
) -> None:
    """The override flows end-to-end from CalendarMergerService down to the
    CalendarFetcher request timeout."""
    SourceFactory(url="http://example.com/basic.ics", calendar=calendar)

    captured: list[int | None] = []
    original = SourceProcessor.fetch_and_validate

    def spy(self: SourceProcessor) -> object:
        captured.append(self.timeout)
        return original(self)

    with patch.object(SourceProcessor, "fetch_and_validate", spy):
        CalendarMergerService(calendar, source_timeout=77).merge()

    assert captured == [77]
