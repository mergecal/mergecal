from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.sites.models import Site
from django.http.request import HttpRequest
from django.http.response import (
    HttpResponse,
    HttpResponseForbidden,
    HttpResponseNotAllowed,
)
from django.shortcuts import get_object_or_404, render
from django.views.decorators.cache import cache_page

from .forms import CalendarForm, SourceForm
from .models import Calendar, Source
from .utils import combine_calendar

# from .tasks import combine_calendar_task


def check_for_demo_account(
    redirect_to="calendars.manage_calendar", error_flash_message=None
):
    def inner_render(fn):
        @wraps(fn)  # Ensure the wrapped function keeps the same name as the view
        def wrapped(request, *args, **kwargs):
            if request.method == "POST" and request.user.email == "demo@example.com":
                if error_flash_message:
                    messages.add_message(
                        request, messages.ERROR, error_flash_message
                    )  # Replace by your own implementation

                return HttpResponseForbidden()
            else:
                return fn(request, *args, **kwargs)

        return wrapped

    return inner_render


@login_required
@check_for_demo_account(error_flash_message="Oops, create an account to do that. 🤐")
def manage_calendar(request):
    calendars = Calendar.objects.filter(owner=request.user)
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
        else:
            return render(
                request, "calendars/partials/calendar_form.html", context={"form": form}
            )

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
        ]
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
            # combine_calendar_task.delay(pk)
            messages.success(request, "Your calendar link has been added")
            return render(
                request,
                "calendars/partials/source_detail.html",
                context={"source": source},
            )
        else:
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
            # combine_calendar_task.delay(source.calendar.id)
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
        ]
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
        f"Your calendar now {'includes' if calendar.include_source else 'excludes'} the source in event title",
    )
    return HttpResponse("")


@cache_page(60 * 15)  # Cache for 15 minutes
def calendar_file(request, uuid):
    calendar = get_object_or_404(Calendar, uuid=uuid)
    combine_calendar(calendar)
    calendar_str = calendar.calendar_file_str
    response = HttpResponse(calendar_str, content_type="text/calendar")
    response["Content-Disposition"] = f'attachment; filename="{uuid}.ics"'

    return response


def calendar_view(request: HttpRequest, uuid: str) -> HttpResponse:
    calendar = get_object_or_404(Calendar, uuid=uuid)
    return render(
        request, "calendars/calendar_view.html", context={"calendar": calendar}
    )
