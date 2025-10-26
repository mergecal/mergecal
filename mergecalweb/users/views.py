import logging

from django.contrib import messages
from django.contrib.auth import logout
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.shortcuts import redirect
from django.urls import reverse
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import FormView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from mergecalweb.billing.tasks import update_stripe_subscription
from mergecalweb.core.emails import TemplateEmailMessage
from mergecalweb.core.logging_events import LogEvent
from mergecalweb.users.forms import AccountDeleteForm
from mergecalweb.users.models import User
from mergecalweb.users.services import delete_user_account

logger = logging.getLogger(__name__)


class UserDetailView(LoginRequiredMixin, DetailView):
    model = User
    slug_field = "username"
    slug_url_kwarg = "username"

    def get(self, request, *args, **kwargs):
        profile_username = kwargs.get("username")
        viewer = request.user

        logger.debug(
            "User accessing profile page",
            extra={
                "event": LogEvent.USER_PROFILE_VIEW,
                "profile_username": profile_username,
                "viewer_id": viewer.pk,
                "viewer_username": viewer.username,
                "is_own_profile": profile_username == viewer.username,
            },
        )

        response = super().get(request, *args, **kwargs)

        logger.info(
            "Triggering subscription sync for profile user",
            extra={
                "event": LogEvent.USER_PROFILE_SUBSCRIPTION_SYNC,
                "user_id": self.object.pk,
                "username": self.object.username,
                "email": self.object.email,
                "current_tier": self.object.subscription_tier,
            },
        )
        update_stripe_subscription(self.object.id)

        return response


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = User
    fields = ["name"]
    success_message = _("Information successfully updated")

    def get_success_url(self) -> str:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user.get_absolute_url()

    def get_object(self, queryset: QuerySet | None = None) -> User:
        assert self.request.user.is_authenticated  # type guard
        return self.request.user

    def form_valid(self, form):
        user = self.request.user
        old_name = user.name
        new_name = form.cleaned_data.get("name")

        logger.info(
            "User updated profile information",
            extra={
                "event": LogEvent.USER_PROFILE_UPDATED,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "old_name": old_name,
                "new_name": new_name,
            },
        )
        return super().form_valid(form)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    permanent = False

    def get_redirect_url(self):
        return reverse("calendars:calendar_list")


user_redirect_view = UserRedirectView.as_view()


class AccountDeleteView(LoginRequiredMixin, FormView):
    """
    View for account deletion with confirmation.
    Shows deletion preview and requires password confirmation.
    """

    template_name = "users/user_confirm_delete.html"
    form_class = AccountDeleteForm
    success_url = reverse_lazy("home")

    def get_form_kwargs(self):
        """Pass the current user and request to the form."""
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        kwargs["request"] = self.request
        return kwargs

    def get_context_data(self, **kwargs):
        """Add deletion preview data to context."""
        context = super().get_context_data(**kwargs)
        user = self.request.user

        # Get all calendars with their sources
        calendars = user.calendar_set.prefetch_related("calendarOf").all()

        # Calculate totals
        total_calendars = calendars.count()
        total_sources = sum(calendar.calendarOf.count() for calendar in calendars)

        context.update(
            {
                "calendars": calendars,
                "total_calendars": total_calendars,
                "total_sources": total_sources,
            },
        )

        logger.debug(
            "Account deletion preview displayed",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_PREVIEW,
                "user_id": user.pk,
                "username": user.username,
                "calendar_count": total_calendars,
                "source_count": total_sources,
            },
        )

        return context

    def form_valid(self, form):
        """Handle successful form submission - delete the account."""
        user = self.request.user
        user_email = user.email
        user_username = user.username

        logger.info(
            "Account deletion form submitted",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_FORM_SUBMITTED,
                "user_id": user.pk,
                "username": user_username,
                "email": user_email,
            },
        )

        # Send confirmation email BEFORE deletion
        self._send_deletion_email(user)

        # Delete the account
        delete_user_account(user)

        # Log out the user (must happen after deletion service call)
        logout(self.request)

        # Add success message
        messages.success(
            self.request,
            _(
                "Your account has been successfully deleted. "
                "A confirmation email has been sent to {email}.",
            ).format(email=user_email),
        )

        logger.info(
            "User logged out after account deletion",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_LOGOUT,
                "username": user_username,
                "email": user_email,
            },
        )

        return redirect(self.success_url)

    def _send_deletion_email(self, user):
        """Send account deletion confirmation email."""
        email_body = _(
            "Your MergeCal account has been permanently deleted.\n\n"
            "All your calendars and sources have been removed. "
            "Your payment history and invoices will be retained for "
            "legal compliance.\n\n"
            "If you have any questions or concerns, please contact us at "
            "support@mergecal.com.",
        )

        email = TemplateEmailMessage(
            subject=_("Your MergeCal account has been deleted"),
            to_users=[user],
            body=email_body,
        )
        email.send()

        logger.info(
            "Account deletion confirmation email sent",
            extra={
                "event": LogEvent.ACCOUNT_DELETION_EMAIL_SENT,
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
            },
        )


account_delete_view = AccountDeleteView.as_view()
