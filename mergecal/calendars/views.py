import logging
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.http import Http404
from django.http.request import HttpRequest
from django.http.response import HttpResponse
from django.http.response import HttpResponseForbidden
from django.http.response import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .forms import CalendarForm
from .forms import SourceForm
from .models import Calendar
from .models import Source
from .utils import combine_calendar

logger = logging.getLogger(__name__)


def check_for_demo_account(
    redirect_to="calendars.manage_calendar",
    error_flash_message=None,
):
    def inner_render(fn):
        @wraps(fn)  # Ensure the wrapped function keeps the same name as the view
        def wrapped(request, *args, **kwargs):
            if request.method == "POST" and request.user.email == "demo@example.com":
                if error_flash_message:
                    messages.add_message(
                        request,
                        messages.ERROR,
                        error_flash_message,
                    )  # Replace by your own implementation

                return HttpResponseForbidden()
            return fn(request, *args, **kwargs)

        return wrapped

    return inner_render


@login_required
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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


@login_required
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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
def create_calendar_form(request):
    form = CalendarForm()
    context = {"form": form}
    return render(request, "calendars/partials/calendar_form.html", context)


@login_required
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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


@login_required
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
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
def detail_source(request, pk):
    source = get_object_or_404(Source, id=pk)
    context = {"source": source}
    return render(request, "calendars/partials/source_detail.html", context)


@login_required
def create_source_form(request, pk):
    calendar = get_object_or_404(Calendar.objects.filter(owner=request.user), pk=pk)
    form = SourceForm()
    context = {"form": form, "calendar": calendar}
    return render(request, "calendars/partials/source_form.html", context)


@login_required
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
            calendar = get_object_or_404(Calendar, uuid=uuid)
        except Http404:
            return Response(
                {"error": "Calendar not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        origin_domain = self.request.GET.get("origin", "")

        combine_calendar(calendar, origin_domain)

        calendar_str = calendar.calendar_file_str
        if not calendar_str:
            return Response(
                {"error": "Failed to generate calendar data"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(calendar_str, content_type="text/calendar")
        response["Content-Disposition"] = f'attachment; filename="{uuid}.ics"'  # E702
        return response


def calendar_view(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar = get_object_or_404(Calendar, uuid=uuid)
    logger.info("User %s is viewing the calendar view page", request.user)
    return render(
        request,
        "calendars/calendar_view.html",
        context={"calendar": calendar},
    )
