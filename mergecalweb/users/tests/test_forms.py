"""Module for all Form Tests."""

import pytest
from django.utils.translation import gettext_lazy as _

from mergecalweb.users.forms import AccountDeleteForm
from mergecalweb.users.forms import UserAdminCreationForm
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db


class TestUserAdminCreationForm:
    """
    Test class for all tests related to the UserAdminCreationForm
    """

    def test_username_validation_error_msg(self, user: User):
        """
        Tests UserAdminCreation Form's unique validator functions correctly by testing:
            1) A new user with an existing username cannot be added.
            2) Only 1 error is raised by the UserCreation Form
            3) The desired error message is raised
        """

        # The user already exists,
        # hence cannot be created.
        form = UserAdminCreationForm(
            {
                "username": user.username,
                "password1": user.password,
                "password2": user.password,
            },
        )

        assert not form.is_valid()
        assert len(form.errors) == 1
        assert "username" in form.errors
        assert form.errors["username"][0] == _("This username has already been taken.")


class TestAccountDeleteForm:
    """Test class for AccountDeleteForm."""

    def test_valid_form_with_correct_password(self):
        """Form should be valid with correct password and confirmation."""
        user = UserFactory()
        user.set_password("test_password")
        user.save()

        form_data = {
            "password": "test_password",
            "confirm_deletion": True,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert form.is_valid()

    def test_invalid_form_with_incorrect_password(self):
        """Form should be invalid with incorrect password."""
        user = UserFactory()
        user.set_password("correct_password")
        user.save()

        form_data = {
            "password": "wrong_password",
            "confirm_deletion": True,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert not form.is_valid()
        assert "password" in form.errors
        assert form.errors["password"][0] == _(
            "The password you entered is incorrect. Please try again.",
        )

    def test_invalid_form_without_confirmation(self):
        """Form should be invalid without confirmation checkbox."""
        user = UserFactory()
        user.set_password("test_password")
        user.save()

        form_data = {
            "password": "test_password",
            "confirm_deletion": False,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert not form.is_valid()
        assert "confirm_deletion" in form.errors

    def test_form_requires_both_fields(self):
        """Form should require both password and confirmation."""
        user = UserFactory()

        form_data = {}
        form = AccountDeleteForm(user=user, data=form_data)
        assert not form.is_valid()
        assert "password" in form.errors
        assert "confirm_deletion" in form.errors

    def test_form_initializes_with_user(self):
        """Form should initialize with user instance."""
        user = UserFactory()
        form = AccountDeleteForm(user=user)
        assert form.user == user

    def test_password_field_has_correct_widget(self):
        """Password field should use PasswordInput widget."""
        user = UserFactory()
        form = AccountDeleteForm(user=user)
        assert form.fields["password"].widget.__class__.__name__ == "PasswordInput"

    def test_confirmation_checkbox_required(self):
        """Confirmation checkbox should be required."""
        user = UserFactory()
        form = AccountDeleteForm(user=user)
        assert form.fields["confirm_deletion"].required is True
