from mergecalweb.calendars.fetching.fetcher import BrokenSourceUrlError
from mergecalweb.calendars.fetching.fetcher import SourceAccessDeniedError
from mergecalweb.calendars.fetching.fetcher import SourceFetchError
from mergecalweb.calendars.fetching.fetcher import SourceTimeoutError
from mergecalweb.calendars.fetching.fetcher import SourceUnavailableError


def describe_fetch_error(error: SourceFetchError) -> str:
    if isinstance(error, SourceTimeoutError):
        return "The calendar server took too long to respond."
    if isinstance(error, SourceAccessDeniedError):
        return (
            f"The calendar server refused access (HTTP {error.status_code}). "
            "The calendar may no longer be shared, or the server may be "
            "blocking automated requests."
        )
    if isinstance(error, BrokenSourceUrlError) and error.status_code is not None:
        return (
            f"The calendar URL returned HTTP {error.status_code}. "
            "Check that it is correct and still shared."
        )
    if isinstance(error, BrokenSourceUrlError):
        return "The calendar URL can't be reached as written. Check that it is correct."
    if isinstance(error, SourceUnavailableError) and error.status_code is not None:
        return (
            f"The calendar server returned HTTP {error.status_code}. "
            "It may be temporarily down."
        )
    return "Could not connect to the calendar server."
