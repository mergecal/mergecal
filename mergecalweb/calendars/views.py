import logging
import time

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.db.models import Prefetch
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views import View
from django.views.decorators.clickjacking import xframe_options_exempt
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import ListView
from django.views.generic import UpdateView

from mergecalweb.calendars.forms import CalendarForm
from mergecalweb.calendars.forms import SourceForm
from mergecalweb.calendars.models import Calendar
from mergecalweb.calendars.models import Source
from mergecalweb.calendars.services.calendar_merger_service import CalendarMergerService
from mergecalweb.core.utils import get_site_url

logger = logging.getLogger(__name__)


class UserCalendarListView(LoginRequiredMixin, ListView):
    model = Calendar
    template_name = "calendars/calendar_list.html"
    context_object_name = "calendars"

    def get_queryset(self):
        return (
            Calendar.objects.filter(owner=self.request.user)
            .annotate(source_count=Count("calendarOf"))
            .prefetch_related(
                Prefetch(
                    "calendarOf",
                    queryset=Source.objects.all()[:5],
                    to_attr="recent_sources",
                ),
            )
            .select_related("owner")
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["total_calendars"] = self.get_queryset().count()
        context["total_sources"] = sum(
            calendar.source_count for calendar in context["calendars"]
        )
        context["domain_name"] = get_site_url()
        return context

    def get(self, request, *args, **kwargs):
        calendars = self.get_queryset()

        if calendars.count() == 0:
            messages.info(
                request,
                "Create a calendar to get started.",
            )
            return redirect(reverse("calendars:calendar_create"))

        return super().get(request, *args, **kwargs)


class CalendarCreateView(LoginRequiredMixin, CreateView):
    model = Calendar
    form_class = CalendarForm
    template_name = "calendars/calendar_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Calendar created successfully.")
        user = self.request.user
        calendar = form.instance
        logger.info(
            "User created new calendar",
            extra={
                "event": "calendar_created",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "user_tier": user.subscription_tier,
            },
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("calendars:calendar_update", kwargs={"uuid": self.object.uuid})


class CalendarUpdateView(LoginRequiredMixin, UpdateView):
    model = Calendar
    form_class = CalendarForm
    template_name = "calendars/calendar_form.html"
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["domain_name"] = get_site_url()
        return context

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Calendar updated successfully.")
        user = self.request.user
        calendar = form.instance
        logger.info(
            "User updated calendar",
            extra={
                "event": "calendar_updated",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "user_tier": user.subscription_tier,
            },
        )
        return super().form_valid(form)


class CalendarDeleteView(LoginRequiredMixin, DeleteView):
    model = Calendar
    success_url = reverse_lazy("calendars:calendar_list")
    slug_field = "uuid"
    slug_url_kwarg = "uuid"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Calendar deleted successfully.")
        user = self.request.user
        calendar = self.get_object()
        logger.info(
            "User deleted calendar",
            extra={
                "event": "calendar_deleted",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "user_tier": user.subscription_tier,
            },
        )
        return super().delete(request, *args, **kwargs)


class SourceAddView(LoginRequiredMixin, CreateView):
    model = Source
    form_class = SourceForm
    template_name = "calendars/source_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.calendar = get_object_or_404(
            Calendar,
            uuid=self.kwargs["uuid"],
            owner=self.request.user,
        )

    def form_valid(self, form):
        form.instance.calendar.uuid = self.kwargs["uuid"]
        messages.success(self.request, "Source added successfully.")
        user = self.request.user
        source = form.instance
        logger.info(
            "User added source to calendar",
            extra={
                "event": "source_added",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": self.calendar.uuid,
                "calendar_name": self.calendar.name,
                "source_name": source.name,
                "source_url": source.url,
                "user_tier": user.subscription_tier,
            },
        )
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["calendar"] = self.calendar
        return context

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["calendar"] = self.calendar
        return kwargs

    def get_success_url(self):
        return reverse(
            "calendars:calendar_update",
            kwargs={"uuid": self.kwargs["uuid"]},
        )


class SourceEditView(LoginRequiredMixin, UpdateView):
    model = Source
    form_class = SourceForm
    template_name = "calendars/source_form.html"

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        if obj.calendar.owner != self.request.user:
            error_message = "You don't have permission to edit this source."
            raise PermissionDenied(error_message)
        return obj

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["calendar"] = self.object.calendar
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["calendar"] = self.object.calendar
        return context

    def form_valid(self, form):
        form.instance.calendar = self.object.calendar
        messages.success(self.request, "Source updated successfully.")
        user = self.request.user
        source = form.instance
        logger.info(
            "User updated source",
            extra={
                "event": "source_updated",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": source.calendar.uuid,
                "calendar_name": source.calendar.name,
                "source_id": source.pk,
                "source_name": source.name,
                "source_url": source.url,
                "user_tier": user.subscription_tier,
            },
        )
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            "calendars:calendar_update",
            kwargs={"uuid": self.object.calendar.uuid},
        )


@require_POST
@login_required
def source_delete(request, pk):
    source = get_object_or_404(Source, pk=pk, calendar__owner=request.user)
    uuid = source.calendar.uuid
    user = request.user

    logger.info(
        "User deleted source from calendar",
        extra={
            "event": "source_deleted",
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "calendar_uuid": source.calendar.uuid,
            "calendar_name": source.calendar.name,
            "source_id": source.pk,
            "source_name": source.name,
            "source_url": source.url,
            "user_tier": user.subscription_tier,
        },
    )
    source.delete()
    messages.success(request, "Source deleted successfully.")
    return redirect("calendars:calendar_update", uuid=uuid)


class CalendarFileView(View):
    def get(self, request, uuid):
        return self.process_calendar_request(request, uuid)

    def post(self, request, uuid):
        return self.process_calendar_request(request, uuid)

    def process_calendar_request(self, request, uuid):
        start_time = time.time()
        user_agent = request.headers.get("user-agent", "Unknown")
        ip_address = request.META.get("REMOTE_ADDR", "Unknown")
        referer = request.headers.get("referer", "Unknown")

        calendar = get_object_or_404(
            Calendar.objects.select_related("owner"),
            uuid=uuid,
        )

        # Capture the embed URL if provided
        embed_url = request.GET.get("embed_url")

        logger.info(
            "Calendar file access request",
            extra={
                "event": "calendar_file_access",
                "calendar_uuid": uuid,
                "calendar_name": calendar.name,
                "owner_id": calendar.owner.pk,
                "owner_username": calendar.owner.username,
                "owner_tier": calendar.owner.subscription_tier,
                "request_method": request.method,
                "user_agent": user_agent[:100],
                "ip_address": ip_address,
                "referer": referer[:100],
                "embed_url": embed_url[:200] if embed_url else None,
                "is_embedded": bool(embed_url),
            },
        )

        merger = CalendarMergerService(calendar)
        calendar_str = merger.merge()

        if not calendar_str:
            logger.error(
                "Calendar merge failed during file access",
                extra={
                    "event": "calendar_file_merge_failed",
                    "calendar_uuid": uuid,
                    "calendar_name": calendar.name,
                    "owner_id": calendar.owner.pk,
                    "owner_username": calendar.owner.username,
                },
            )
            return HttpResponse(
                "Failed to generate calendar data",
                status=500,
                content_type="text/plain",
            )

        response = HttpResponse(calendar_str, content_type="text/calendar")
        response["Content-Disposition"] = f'attachment; filename="{uuid}.ics"'
        if getattr(calendar.owner, "is_free_tier", False):
            response["Cache-Control"] = "public, max-age=43200"  # 12 hours in seconds

        request_duration = time.time() - start_time
        logger.info(
            "Calendar file served successfully",
            extra={
                "event": "calendar_file_success",
                "calendar_uuid": uuid,
                "calendar_name": calendar.name,
                "owner_id": calendar.owner.pk,
                "owner_username": calendar.owner.username,
                "owner_tier": calendar.owner.subscription_tier,
                "file_size_bytes": len(calendar_str),
                "duration_seconds": round(request_duration, 2),
                "is_free_tier": calendar.owner.is_free_tier,
            },
        )

        return response


def calendar_view(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar = get_object_or_404(Calendar, uuid=uuid)
    user = request.user

    if user.is_authenticated:
        logger.info(
            "User viewing calendar web page",
            extra={
                "event": "calendar_web_view",
                "user_id": user.pk,
                "username": user.username,
                "email": user.email,
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
                "is_owner": calendar.owner == user,
            },
        )
    else:
        logger.info(
            "Anonymous user viewing calendar web page",
            extra={
                "event": "calendar_web_view_anonymous",
                "calendar_uuid": calendar.uuid,
                "calendar_name": calendar.name,
            },
        )

    return render(
        request,
        "calendars/calendar_view.html",
        context={"calendar": calendar},
    )


@xframe_options_exempt
def calendar_iframe(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar = get_object_or_404(Calendar, uuid=uuid)
    referer = request.headers.get("referer")

    logger.info(
        "Calendar iframe embedded on external site",
        extra={
            "event": "calendar_iframe_view",
            "calendar_uuid": calendar.uuid,
            "calendar_name": calendar.name,
            "owner_id": calendar.owner.pk,
            "owner_username": calendar.owner.username,
            "referer": referer[:200] if referer else None,
            "has_referer": bool(referer),
        },
    )

    return render(
        request,
        "calendars/calendar_iframe.html",
        {"calendar": calendar, "embed_referer": referer},
    )


@staff_member_required
def url_validator(request: HttpRequest) -> HttpResponse:
    """
    URL validator view for superusers to validate calendar source URLs.
    """
    user = request.user
    logger.info(
        "Staff member accessed URL validator tool",
        extra={
            "event": "url_validator_access",
            "user_id": user.pk,
            "username": user.username,
            "email": user.email,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
        },
    )

    context = {
        "page_title": "URL Validator",
    }

    return render(request, "calendars/url_validator.html", context)
