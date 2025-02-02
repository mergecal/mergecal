class LocalUrlError(Exception):
    """Raised when a local URL is used in SourceProcessor."""


class CalendarValidationError(ValueError):
    """Raised when calendar data is invalid."""


class CalendarCustomizationError(ValueError):
    """Raised when calendar customization fails."""


class CustomizationWithoutCalendarError(CalendarCustomizationError):
    """Raised when calendar customization is attempted without a calendar."""
