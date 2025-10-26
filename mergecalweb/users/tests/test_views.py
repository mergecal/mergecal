from http import HTTPStatus
from unittest.mock import Mock
from unittest.mock import patch

import pytest
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.models import AnonymousUser
from django.contrib.messages.middleware import MessageMiddleware
from django.contrib.sessions.middleware import SessionMiddleware
from django.http import HttpRequest
from django.http import HttpResponseRedirect
from django.test import RequestFactory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from mergecalweb.calendars.tests.factories import CalendarFactory
from mergecalweb.calendars.tests.factories import SourceFactory
from mergecalweb.users.forms import AccountDeleteForm
from mergecalweb.users.forms import UserAdminChangeForm
from mergecalweb.users.models import User
from mergecalweb.users.tests.factories import UserFactory
from mergecalweb.users.views import AccountDeleteView
from mergecalweb.users.views import UserRedirectView
from mergecalweb.users.views import UserUpdateView
from mergecalweb.users.views import account_delete_view
from mergecalweb.users.views import user_detail_view

pytestmark = pytest.mark.django_db


class TestUserUpdateView:
    """
    TODO:
        extracting view initialization code as class-scoped fixture
        would be great if only pytest-django supported non-function-scoped
        fixture db access -- this is a work-in-progress for now:
        https://github.com/pytest-dev/pytest-django/pull/258
    """

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_get_success_url(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request
        assert view.get_success_url() == f"/users/{user.username}/"

    def test_get_object(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")
        request.user = user

        view.request = request

        assert view.get_object() == user

    def test_form_valid(self, user: User, rf: RequestFactory):
        view = UserUpdateView()
        request = rf.get("/fake-url/")

        # Add the session/message middleware to the request
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)
        request.user = user

        view.request = request

        # Initialize the form
        form = UserAdminChangeForm()
        form.cleaned_data = {}
        form.instance = user
        view.form_valid(form)

        messages_sent = [m.message for m in messages.get_messages(request)]
        assert messages_sent == [_("Information successfully updated")]


class TestUserRedirectView:
    def test_get_redirect_url(self, user: User, rf: RequestFactory):
        view = UserRedirectView()
        request = rf.get("/fake-url")
        request.user = user

        view.request = request
        assert view.get_redirect_url() == "/calendars/"


class TestUserDetailView:
    def test_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = UserFactory()
        response = user_detail_view(request, username=user.username)

        assert response.status_code == HTTPStatus.OK

    def test_not_authenticated(self, user: User, rf: RequestFactory):
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = user_detail_view(request, username=user.username)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"


class TestAccountDeleteView:
    """Tests for account deletion functionality."""

    def dummy_get_response(self, request: HttpRequest):
        return None

    def test_unauthenticated_redirects_to_login(self, rf: RequestFactory):
        """Unauthenticated users should be redirected to login."""
        request = rf.get("/fake-url/")
        request.user = AnonymousUser()
        response = account_delete_view(request)
        login_url = reverse(settings.LOGIN_URL)

        assert isinstance(response, HttpResponseRedirect)
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == f"{login_url}?next=/fake-url/"

    def test_authenticated_user_can_access_deletion_page(
        self,
        user: User,
        rf: RequestFactory,
    ):
        """Authenticated user should be able to access the deletion page."""
        request = rf.get("/fake-url/")
        request.user = user
        response = account_delete_view(request)

        assert response.status_code == HTTPStatus.OK

    def test_deletion_page_shows_correct_calendar_counts(
        self,
        user: User,
        rf: RequestFactory,
    ):
        """Deletion page should display correct calendar and source counts."""
        # Create calendars and sources for the user
        calendar1 = CalendarFactory(owner=user, name="Work Calendar")
        calendar2 = CalendarFactory(owner=user, name="Personal Calendar")
        SourceFactory.create_batch(3, calendar=calendar1)
        SourceFactory.create_batch(2, calendar=calendar2)

        view = AccountDeleteView()
        request = rf.get("/fake-url/")
        request.user = user
        view.request = request

        context = view.get_context_data()

        expected_calendars = 2
        expected_sources = 5
        assert context["total_calendars"] == expected_calendars
        assert context["total_sources"] == expected_sources
        assert len(context["calendars"]) == expected_calendars

    def test_invalid_password_prevents_deletion(self, user: User, rf: RequestFactory):
        """Deletion should fail with incorrect password."""
        user.set_password("correct_password")
        user.save()

        form_data = {
            "password": "wrong_password",
            "confirm_deletion": True,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert not form.is_valid()
        assert "password" in form.errors

    def test_missing_confirmation_checkbox_prevents_deletion(
        self,
        user: User,
        rf: RequestFactory,
    ):
        """Deletion should fail without confirmation checkbox."""
        user.set_password("test_password")
        user.save()

        form_data = {
            "password": "test_password",
            "confirm_deletion": False,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert not form.is_valid()
        assert "confirm_deletion" in form.errors

    @patch("mergecalweb.users.views.delete_user_account")
    @patch("mergecalweb.users.views.TemplateEmailMessage")
    def test_successful_deletion_removes_user_and_cascades(
        self,
        mock_email,
        mock_delete_service,
        user: User,
        rf: RequestFactory,
    ):
        """Successful deletion should remove user and cascade to calendars/sources."""
        # Setup
        user.set_password("test_password")
        user.save()

        calendar1 = CalendarFactory(owner=user)
        calendar2 = CalendarFactory(owner=user)
        SourceFactory.create_batch(2, calendar=calendar1)
        SourceFactory.create_batch(3, calendar=calendar2)

        # Mock the deletion service
        mock_delete_service.return_value = {
            "calendar_count": 2,
            "source_count": 5,
            "deleted_at": "2025-01-01T00:00:00",
            "user_email": user.email,
            "user_username": user.username,
        }

        # Mock email sending
        mock_email_instance = Mock()
        mock_email.return_value = mock_email_instance

        # Create request
        request = rf.post("/fake-url/")
        request.user = user

        # Add middleware
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        # Create view and handle form submission
        view = AccountDeleteView()
        view.request = request
        view.setup(request)

        form_data = {
            "password": "test_password",
            "confirm_deletion": True,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert form.is_valid()

        response = view.form_valid(form)

        # Assertions
        assert response.status_code == HTTPStatus.FOUND
        assert response.url == "/"
        mock_delete_service.assert_called_once_with(user)
        mock_email_instance.send.assert_called_once()

    @patch("mergecalweb.users.views.delete_user_account")
    @patch("mergecalweb.users.views.TemplateEmailMessage")
    def test_user_logged_out_after_deletion(
        self,
        mock_email,
        mock_delete_service,
        user: User,
        client,
    ):
        """User should be logged out after successful deletion."""
        # Setup
        user.set_password("test_password")
        user.save()

        # Mock the deletion service
        mock_delete_service.return_value = {
            "calendar_count": 0,
            "source_count": 0,
            "deleted_at": "2025-01-01T00:00:00",
            "user_email": user.email,
            "user_username": user.username,
        }

        # Mock email
        mock_email_instance = Mock()
        mock_email.return_value = mock_email_instance

        # Login
        client.force_login(user)

        # Submit deletion
        response = client.post(
            reverse("users:delete"),
            {
                "password": "test_password",
                "confirm_deletion": True,
            },
        )

        # User should be logged out
        assert response.status_code == HTTPStatus.FOUND
        assert "_auth_user_id" not in client.session

    @patch("mergecalweb.users.views.delete_user_account")
    @patch("mergecalweb.users.views.TemplateEmailMessage")
    def test_confirmation_email_sent(
        self,
        mock_email,
        mock_delete_service,
        user: User,
        rf: RequestFactory,
    ):
        """Confirmation email should be sent before deletion."""
        user.set_password("test_password")
        user.save()

        # Mock the deletion service
        mock_delete_service.return_value = {
            "calendar_count": 0,
            "source_count": 0,
            "deleted_at": "2025-01-01T00:00:00",
            "user_email": user.email,
            "user_username": user.username,
        }

        # Mock email
        mock_email_instance = Mock()
        mock_email.return_value = mock_email_instance

        # Create request
        request = rf.post("/fake-url/")
        request.user = user

        # Add middleware
        SessionMiddleware(self.dummy_get_response).process_request(request)
        MessageMiddleware(self.dummy_get_response).process_request(request)

        # Create view
        view = AccountDeleteView()
        view.request = request
        view.setup(request)

        form_data = {
            "password": "test_password",
            "confirm_deletion": True,
        }

        form = AccountDeleteForm(user=user, data=form_data)
        assert form.is_valid()

        view.form_valid(form)

        # Email should be sent
        mock_email.assert_called_once()
        mock_email_instance.send.assert_called_once()
