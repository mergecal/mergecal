import requests
from icalendar import Calendar, Timezone


def combine_calendar(calendar_instance):
    newcal = Calendar()
    newcal.add("prodid", "-//" + calendar_instance.name + "//calmerge.habet.dev//")
    newcal.add("version", "2.0")
    newcal.add("x-wr-calname", calendar_instance.name)

    newtimezone = Timezone()
    newtimezone.add("tzid", calendar_instance.timezone)
    newcal.add_component(newtimezone)

    for source in calendar_instance.source_set.all():
        try:
            r = requests.get(source.url)
            print(source.url)
            r.raise_for_status()
            cal = Calendar.from_ical(r.text)
            # every part of the file...
            for component in cal.subcomponents:
                if component.name == "VEVENT":
                    # ...which name is VEVENT will be added to the new file
                    newcal.add_component(component)
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

    print(calendar_instance.calendar_file.name)
    with open(calendar_instance.calendar_file.path, "wb") as f:
        f.write(newcal.to_ical())
