from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Field, Layout
from django.forms import ModelForm

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
        help_texts = {
            "name": "Name you calendar.",
        }

        labels = {
            "timezone": False,
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
