from icalendar import Calendar
from icalendar.timezone.windows_to_olson import WINDOWS_TO_OLSON

DATETIME_PROPS = ("DTSTART", "DTEND", "RECURRENCE-ID", "DUE", "EXDATE", "RDATE")


def normalize_tzids(cal: Calendar) -> Calendar:
    """Normalize Windows timezone IDs in a calendar to IANA timezone IDs."""
    for component in cal.walk():
        for prop_name in DATETIME_PROPS:
            props = component.get(prop_name)
            if props is None:
                continue

            property_values = props if isinstance(props, list) else [props]
            for property_value in property_values:
                tzid = property_value.params.get("TZID")
                if tzid in WINDOWS_TO_OLSON:
                    property_value.params["TZID"] = WINDOWS_TO_OLSON[tzid]

    seen_tzids: set[str] = set()
    normalized_subcomponents = []

    for subcomponent in cal.subcomponents:
        if subcomponent.name == "VTIMEZONE":
            tzid = str(subcomponent.get("TZID", ""))
            if tzid in WINDOWS_TO_OLSON:
                subcomponent["TZID"] = WINDOWS_TO_OLSON[tzid]

            normalized_tzid = str(subcomponent.get("TZID", ""))
            if normalized_tzid in seen_tzids:
                continue
            seen_tzids.add(normalized_tzid)

        normalized_subcomponents.append(subcomponent)

    cal.subcomponents = normalized_subcomponents
    return cal
