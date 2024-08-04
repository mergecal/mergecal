import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.sites.models import Site
from django.db.models import Count
from django.db.models import Prefetch
from django.http import Http404
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.shortcuts import redirect
from django.shortcuts import render
from django.urls import reverse
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView
from django.views.generic import DeleteView
from django.views.generic import ListView
from django.views.generic import UpdateView
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from mergecal.calendars.forms import CalendarForm
from mergecal.calendars.forms import SourceForm
from mergecal.calendars.models import Calendar
from mergecal.calendars.models import Source
from mergecal.calendars.services import CalendarMerger
from mergecal.core.decorators import requires_htmx
from mergecal.core.utils import get_site_url

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


class CalendarCreateView(LoginRequiredMixin, CreateView):
    model = Calendar
    form_class = CalendarForm
    template_name = "calendars/calendar_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Calendar created successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("calendars:calendar_update", kwargs={"pk": self.object.pk})


class CalendarUpdateView(LoginRequiredMixin, UpdateView):
    model = Calendar
    form_class = CalendarForm
    template_name = "calendars/calendar_form.html"

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Calendar updated successfully.")
        return super().form_valid(form)


class CalendarDeleteView(LoginRequiredMixin, DeleteView):
    model = Calendar
    success_url = reverse_lazy("calendars:calendar_list")

    def get_queryset(self):
        return super().get_queryset().filter(owner=self.request.user)

    def delete(self, request, *args, **kwargs):
        messages.success(self.request, "Calendar deleted successfully.")
        return super().delete(request, *args, **kwargs)


class SourceAddView(LoginRequiredMixin, CreateView):
    model = Source
    form_class = SourceForm
    template_name = "calendars/source_form.html"

    def form_valid(self, form):
        form.instance.calendar_id = self.kwargs["calendar_pk"]
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["calendar"] = get_object_or_404(
            Calendar,
            pk=self.kwargs["calendar_pk"],
            owner=self.request.user,
        )
        return context

    def get_success_url(self):
        return reverse(
            "calendars:calendar_update",
            kwargs={"pk": self.kwargs["calendar_pk"]},
        )


class SourceEditView(LoginRequiredMixin, UpdateView):
    model = Source
    form_class = SourceForm
    template_name = "calendars/source_form.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["calendar"] = self.object.calendar
        return context

    def get_success_url(self):
        return reverse(
            "calendars:calendar_update",
            kwargs={"pk": self.object.calendar.pk},
        )


@require_POST
@login_required
def source_delete(request, pk):
    source = get_object_or_404(Source, pk=pk, calendar__owner=request.user)
    calendar_pk = source.calendar.pk
    source.delete()
    messages.success(request, "Source deleted successfully.")
    return redirect("calendars:calendar_update", pk=calendar_pk)


@login_required
def manage_calendar(request):
    calendars = Calendar.objects.filter(owner=request.user).defer("calendar_file_str")
    form = CalendarForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            calendar = form.save(commit=False)
            calendar.owner = request.user
            calendar.save()
            messages.success(request, "Your calendar has been created")
            return render(
                request,
                "calendars/partials/calendar_detail.html",
                context={
                    "calendar": calendar,
                    "domain_name": Site.objects.get_current().domain,
                },
            )
        return render(
            request,
            "calendars/partials/calendar_form.html",
            context={"form": form},
        )
    logger.info("User %s is viewing the manage calendar page", request.user)

    context = {
        "form": form,
        "calendars": calendars,
        "domain_name": Site.objects.get_current().domain,
    }

    return render(request, "calendars/manage_calendar.html", context)


@login_required
def update_calendar(request, pk):
    calendar = Calendar.objects.get(id=pk)
    form = CalendarForm(request.POST or None, instance=calendar)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Your calendar has been updated")
            return render(
                request,
                "calendars/partials/calendar_detail.html",
                context={"calendar": calendar},
            )

    context = {"form": form, "calendar": calendar}

    return render(request, "calendars/partials/calendar_form.html", context)


@requires_htmx
@login_required
def delete_calendar(request, pk):
    calendar = get_object_or_404(Calendar, id=pk)

    if request.method == "POST":
        calendar.delete()
        messages.error(request, "Your calendar has been deleted")
        return HttpResponse("")

    return HttpResponseNotAllowed(
        [
            "POST",
        ],
    )


@login_required
def detail_calendar(request, pk):
    calendar = get_object_or_404(Calendar, id=pk)
    context = {
        "calendar": calendar,
        "domain_name": Site.objects.get_current().domain,
    }
    return render(request, "calendars/partials/calendar_detail.html", context)


@login_required
@requires_htmx
def create_calendar_form(request):
    form = CalendarForm()
    context = {"form": form}
    return render(request, "calendars/partials/calendar_form.html", context)


@login_required
@requires_htmx
def manage_source(request, pk):
    calendar = get_object_or_404(Calendar.objects.filter(owner=request.user), pk=pk)
    sources = Source.objects.filter(calendar=calendar)
    form = SourceForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            source = form.save(commit=False)
            source.calendar = calendar
            source.save()
            messages.success(request, "Your calendar link has been added")
            return render(
                request,
                "calendars/partials/source_detail.html",
                context={"source": source},
            )
        return render(
            request,
            "calendars/partials/source_form.html",
            context={"form": form, "calendar": calendar},
        )
    context = {"form": form, "calendar": calendar, "sources": sources}

    return render(request, "calendars/manage_source.html", context)


@requires_htmx
@login_required
def update_source(request, pk):
    source = Source.objects.get(id=pk)
    form = SourceForm(request.POST or None, instance=source)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            messages.success(request, "Your calendar link has been updated")
            return render(
                request,
                "calendars/partials/source_detail.html",
                context={"source": source},
            )

    context = {"form": form, "source": source}

    return render(request, "calendars/partials/source_form.html", context)


@login_required
@requires_htmx
def delete_source(request, pk):
    source = get_object_or_404(Source, id=pk)

    if request.method == "POST":
        source.delete()
        messages.error(request, "Your calendar link has been deleted")
        return HttpResponse("")

    return HttpResponseNotAllowed(
        [
            "POST",
        ],
    )


@login_required
@requires_htmx
def detail_source(request, pk):
    source = get_object_or_404(Source, id=pk)
    context = {"source": source}
    return render(request, "calendars/partials/source_detail.html", context)


@login_required
@requires_htmx
def create_source_form(request, pk):
    calendar = get_object_or_404(Calendar.objects.filter(owner=request.user), pk=pk)
    form = SourceForm()
    context = {"form": form, "calendar": calendar}
    return render(request, "calendars/partials/source_form.html", context)


@login_required
@requires_htmx
def toggle_include_source(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar: Calendar = get_object_or_404(Calendar, uuid=uuid, owner=request.user)
    calendar.include_source = not calendar.include_source
    calendar.save()
    messages.success(
        request,
        f"Your calendar now {'includes' if calendar.include_source else 'excludes'} the source in event title",  # noqa: E501
    )
    return HttpResponse("")


class CalendarFileAPIView(APIView):
    def get(self, request, uuid):
        return self.process_calendar_request(uuid)

    def post(self, request, uuid):
        return self.process_calendar_request(uuid)

    def process_calendar_request(self, uuid):
        try:
            calendar = get_object_or_404(
                Calendar.objects.select_related("owner"),
                uuid=uuid,
            )
        except Http404:
            return Response(
                {"error": "Calendar not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        merger = CalendarMerger(calendar, self.request)
        calendar_str = merger.merge()

        if not calendar_str:
            return Response(
                {"error": "Failed to generate calendar data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(calendar_str, content_type="text/calendar")
        response["Content-Disposition"] = f'attachment; filename="{uuid}.ics"'  # E702
        if calendar.owner.is_free_tier:
            response["Cache-Control"] = "public, max-age=43200"  # 12 hours in seconds
        return response


def calendar_view(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar = get_object_or_404(Calendar, uuid=uuid)
    logger.info("User %s is viewing the calendar view page", request.user)
    return render(
        request,
        "calendars/calendar_view.html",
        context={"calendar": calendar},
    )
