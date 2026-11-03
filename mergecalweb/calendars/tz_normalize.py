from icalendar import Calendar
from icalendar.timezone.windows_to_olson import WINDOWS_TO_OLSON

DATETIME_PROPS = ("DTSTART", "DTEND", "RECURRENCE-ID", "DUE", "EXDATE", "RDATE")


def normalize_tzids(cal: Calendar) -> Calendar:
    """Mutate a calendar in-place and return the same object for chaining.

    Uses ``WINDOWS_TO_OLSON`` to rewrite Windows TZIDs on supported date-time
    properties (``DTSTART``, ``DTEND``, ``RECURRENCE-ID``, ``DUE``, ``EXDATE``,
    ``RDATE``) and to rename ``VTIMEZONE`` ``TZID`` values, dropping duplicate
    ``VTIMEZONE`` components that collide after normalization.

    Args:
        cal: Parsed iCalendar object to normalize.

    Returns:
        The same ``Calendar`` instance after in-place normalization.
    """
    _normalize_property_tzids(cal)
    _normalize_vtimezones(cal)
    return cal


def _normalize_property_tzids(cal: Calendar) -> None:
    """Rewrite Windows TZIDs to IANA TZIDs on supported date-time properties."""
    for component in cal.walk():
        for prop_name in DATETIME_PROPS:
            props = component.get(prop_name)
            if props is None:
                continue

            property_values = props if isinstance(props, list) else [props]
            for property_value in property_values:
                params = getattr(property_value, "params", None)
                if params is None:
                    continue

                tzid = params.get("TZID")
                if tzid in WINDOWS_TO_OLSON:
                    params["TZID"] = WINDOWS_TO_OLSON[tzid]


def _normalize_vtimezones(cal: Calendar) -> None:
    """Rename VTIMEZONE TZIDs and drop duplicates after normalization."""
    seen_tzids: set[str] = set()
    normalized_subcomponents = []

    for subcomponent in cal.subcomponents:
        if subcomponent.name != "VTIMEZONE":
            normalized_subcomponents.append(subcomponent)
            continue

        tzid = subcomponent.get("TZID")
        final_tzid = (
            None if tzid is None else WINDOWS_TO_OLSON.get(str(tzid), str(tzid))
        )
        if final_tzid is not None:
            subcomponent["TZID"] = final_tzid
            if final_tzid in seen_tzids:
                continue
            seen_tzids.add(final_tzid)

        normalized_subcomponents.append(subcomponent)

    cal.subcomponents = normalized_subcomponents
