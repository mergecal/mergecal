from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.UserCreationForm):
    """
    Form for User Creation in the Admin Area.
    To change user signup, see UserSignupForm and UserSocialSignupForm.
    """

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """
    Form that will be rendered on a user sign up section/screen.
    Default fields will be added automatically.
    Check UserSocialSignupForm for accounts created from social.
    """


class UserSocialSignupForm(SocialSignupForm):
    """
    Renders the form when user has signed up using social accounts.
    Default fields will be added automatically.
    See UserSignupForm otherwise.
    """


class AccountDeleteForm(forms.Form):
    """
    Form for account deletion with password confirmation.
    Requires password verification and explicit confirmation checkbox.
    """

    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter your password to confirm",
                "autocomplete": "current-password",
            },
        ),
        help_text=_("Enter your password to verify it's really you."),
    )

    confirm_deletion = forms.BooleanField(
        label=_("I understand this is permanent and cannot be undone"),
        required=True,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, user, request=None, *args, **kwargs):
        """Initialize form with the user to be deleted."""
        self.user = user
        self.request = request
        super().__init__(*args, **kwargs)

    def clean_password(self):
        """
        Validate that the password matches the user's password.
        Uses Django's authenticate() for additional security features.
        """
        password = self.cleaned_data.get("password")

        # Use authenticate() instead of check_password() for better security
        # authenticate() provides hooks for rate limiting and other security features
        authenticated_user = authenticate(
            request=self.request,
            username=self.user.username,
            password=password,
        )

        if authenticated_user is None or authenticated_user.pk != self.user.pk:
            raise forms.ValidationError(
                _("The password you entered is incorrect. Please try again."),
            )

        return password
