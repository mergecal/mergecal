from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.http.response import HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render

from .forms import CalendarForm, SourceForm
from .models import Calendar, Source
from .tasks import combine_calendar_task


@login_required
def manage_calendar(request):
    calendars = Calendar.objects.filter(owner=request.user)
    form = CalendarForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            calendar = form.save(commit=False)
            calendar.owner = request.user
            calendar.calendar_file.save(f"{calendar.uuid}.ical", ContentFile(b""))
            calendar.save()
            messages.success(request, "Your calendar has been created")
            return render(
                request,
                "calendars/partials/calendar_detail.html",
                context={"calendar": calendar},
            )
        else:
            return render(
                request, "calendars/partials/calendar_form.html", context={"form": form}
            )

    context = {
        "form": form,
        "calendars": calendars,
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
        ]
    )


@login_required
def create_calendar_form(request):
    form = CalendarForm()
    context = {"form": form}
    return render(request, "calendars/partials/calendar_form.html", context)


@login_required
def manage_source(request, pk):
    calendar = get_object_or_404(Calendar.objects.filter(owner=request.user), pk=pk)
    sources = Source.objects.filter(calendar=calendar)
    form = SourceForm(request.POST or None)

    if request.method == "POST":
        if form.is_valid():
            source = form.save(commit=False)
            source.calendar = calendar
            source.save()
            combine_calendar_task.delay(pk)
            messages.success(request, "Your calendar link has been added")
            return render(
                request,
                "calendars/partials/source_detail.html",
                context={"source": source},
            )
        else:
            return render(
                request, "calendars/partials/source_form.html", context={"form": form}
            )

    context = {"form": form, "calendar": calendar, "sources": sources}

    return render(request, "calendars/manage_source.html", context)


@login_required
def update_source(request, pk):
    source = Source.objects.get(id=pk)
    form = SourceForm(request.POST or None, instance=source)

    if request.method == "POST":
        if form.is_valid():
            combine_calendar_task.delay(source.calendar.id)
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
def create_source_form(request, pk):
    calendar = get_object_or_404(Calendar.objects.filter(owner=request.user), pk=pk)
    form = SourceForm()
    context = {"form": form, "calendar": calendar}
    return render(request, "calendars/partials/source_form.html", context)
