from django.forms import ModelForm

from .models import Calendar, Source


class CalendarForm(ModelForm):
    class Meta:
        model = Calendar
        fields = (
            "name",
            "timezone",
        )


class SourceForm(ModelForm):
    class Meta:
        model = Source
        fields = (
            "name",
            "url",
        )
