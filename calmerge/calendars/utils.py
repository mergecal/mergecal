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

    for source in calendar_instance.calendarOf.all():
        try:
            r = requests.get(source.url)
            r.raise_for_status()
            cal = Calendar.from_ical(r.text)
            # every part of the file...
            for component in cal.subcomponents:
                if component.name == "VEVENT":
                    # ...which name is VEVENT will be added to the new file
                    newcal.add_component(component)
        except requests.exceptions.HTTPError as err:
            raise SystemExit(err)

    cal_bye_str = newcal.to_ical()
    calendar_instance.calendar_file_str = cal_bye_str.decode("utf8")
    calendar_instance.save()
