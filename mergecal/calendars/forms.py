# ruff: noqa: FBT001, FBT002
from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Field
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django.forms import ModelForm

from .models import Calendar
from .models import Source


class CalendarForm(ModelForm):
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_tag = False
        self.helper.layout = Layout(
            Div(
                Div(Field("name"), css_class="col-md-6"),
                Div(Field("timezone"), css_class="col-md-6"),
                css_class="row",
            ),
            Div(
                Div(
                    Field("update_frequency_seconds"),
                    HTML(
                        "{% if not user.can_set_update_frequency %}<small class='text-muted'>Upgrade to set update frequency</small>{% endif %}",  # noqa: E501
                    ),
                    css_class="col-md-6",
                ),
                Div(
                    Field("remove_branding"),
                    HTML(
                        "{% if not user.can_remove_branding %}<small class='text-muted'>Upgrade to remove branding</small>{% endif %}",  # noqa: E501
                    ),
                    css_class="col-md-6",
                ),
                css_class="row",
            ),
        )

        if not self.user.can_set_update_frequency:
            self.fields["update_frequency_seconds"].disabled = True
        if not self.user.can_remove_branding:
            self.fields["remove_branding"].disabled = True

    class Meta:
        model = Calendar
        fields = (
            "name",
            "timezone",
            "update_frequency_seconds",
            "remove_branding",
        )

    def clean(self):
        self.instance.owner = self.user
        return super().clean()


class SourceForm(ModelForm):
    class Meta:
        model = Source
        fields = (
            "name",
            "url",
            "include_title",
            "include_description",
            "include_location",
            "custom_prefix",
            "exclude_keywords",
        )

    def __init__(self, *args, **kwargs):
        self.calendar = kwargs.pop("calendar", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        premium_fields = [
            "include_title",
            "include_description",
            "include_location",
            "custom_prefix",
            "exclude_keywords",
        ]

        for field in premium_fields:
            if not self.calendar.owner.can_customize_sources:
                self.fields[field].disabled = True
                self.fields[
                    field
                ].help_text = "Available on Business and Supporter plans"

        self.helper.layout = Layout(
            Field("name", css_class="form-control"),
            Field("url", css_class="form-control"),
            Div(
                Field("include_title"),
                Field("include_description"),
                Field("include_location"),
                Field("custom_prefix", css_class="form-control"),
                Field("exclude_keywords", css_class="form-control"),
                css_class="premium-fields",
            ),
            Submit("submit", "Save", css_class="btn btn-primary"),
        )

    def clean(self):
        self.instance.calendar = self.calendar
        return super().clean()
