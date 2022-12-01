from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django.forms import ModelForm, Select, TextInput

from .models import Calendar, Source


class CalendarForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.field_template = "bootstrap5/layout/inline_field.html"
        self.helper.layout = Layout(
            Div("name", css_class="col"),
            Div(
                Field("timezone", wrapper_class="text-capitalize"), css_class="col-sm-3"
            ),
        )

    class Meta:
        model = Calendar
        fields = (
            "name",
            "timezone",
        )

        labels = {
            "timezone": False,
        }
        widgets = {
            "name": TextInput(attrs={"title": "Give your calendar a name"}),
            "timezone": Select(attrs={"title": "Choose a timezone for your calendar"}),
        }


class SourceForm(ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.field_template = "bootstrap5/layout/inline_field.html"
        self.helper.layout = Layout(
            Div("name", css_class="col-sm-3"),
            Div("url", css_class="col"),
        )

    class Meta:
        model = Source
        fields = (
            "name",
            "url",
        )
        widgets = {
            "name": TextInput(attrs={"title": "Name the external calendar"}),
            "url": TextInput(attrs={"title": "Add Link to the external calendar"}),
        }
