# ruff: noqa: FBT001, FBT002
from crispy_forms.bootstrap import Div
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML
from crispy_forms.layout import Field
from crispy_forms.layout import Layout
from crispy_forms.layout import Submit
from django.forms import ModelForm
from django.forms import ValidationError

from mergecal.core.constants import SOURCE_LIMITS

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
            Div(
                Field("include_source"),
                css_class="col-md-6",
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
            "include_source",
        )

    def clean(self):
        self.instance.owner = self.user
        return super().clean()


class SourceForm(ModelForm):
    class Meta:
        model = Source
        fields = ["name", "url"]

    def __init__(self, *args, **kwargs):
        self.calendar = kwargs.pop("calendar", None)
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        # add submit button
        self.helper.layout = Layout(
            Div(
                Field("name", css_class="form-control"),
                Field("url", css_class="form-control"),
                css_class="form-row",
            ),
            Div(Submit("submit", "Save")),
        )

    def clean(self):
        cleaned_data = super().clean()
        if self.calendar:
            calendar_source_count = (
                Source.objects.filter(calendar=self.calendar)
                .exclude(pk=self.instance.pk)
                .count()
            )
            limit = SOURCE_LIMITS.get(
                self.calendar.owner.subscription_tier,
                float("inf"),
            )
            if calendar_source_count >= limit:
                error_message = (
                    f"Users on the {self.calendar.owner.get_subscription_tier_display()} "  # noqa: E501
                    f"are limited to {limit} sources per calendar."
                )
                raise ValidationError(error_message)
        return cleaned_data

    def save(self, commit: bool = True):
        instance = super().save(commit=False)
        if self.calendar:
            instance.calendar = self.calendar
        if commit:
            instance.save()
        return instance
