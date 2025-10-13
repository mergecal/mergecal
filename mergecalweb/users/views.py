import logging

from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView
from django.views.generic import RedirectView
from django.views.generic import UpdateView

from mergecalweb.billing.tasks import update_stripe_subscription
from mergecalweb.users.models import User

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
                "event": "user_profile_view",
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
                "event": "user_profile_subscription_sync",
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
                "event": "user_profile_updated",
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
