from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from people.models import Person

from .forms import LifeEventForm
from .models import LifeEvent


@login_required
def life_dashboard(request):
    dependents = (
        Person.objects.filter(role="dependent").prefetch_related("life_events").order_by("name")
    )
    dep_events = [event for dep in dependents for event in dep.life_events.all()]

    household_events = (
        LifeEvent.objects.filter(person__isnull=False)
        .select_related("person")
        .order_by("event_year_override")
    )

    all_events = dep_events + list(household_events)
    all_events.sort(key=lambda e: (e.event_year or 9999, e.owner_name))

    return render(
        request,
        "life/dashboard.html",
        {
            "dependents": dependents,
            "timeline": all_events,
        },
    )


@login_required
def life_event_add(request):
    form = LifeEventForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Life event added.")
        return redirect("life_dashboard")
    return render(request, "life/event_form.html", {"form": form, "title": "Add Life Event"})


@login_required
def life_event_edit(request, pk):
    event = get_object_or_404(LifeEvent, pk=pk)
    form = LifeEventForm(request.POST or None, instance=event)
    if form.is_valid():
        form.save()
        messages.success(request, "Life event updated.")
        return redirect("life_dashboard")
    return render(request, "life/event_form.html", {"form": form, "title": "Edit Life Event"})


@login_required
def life_event_delete(request, pk):
    event = get_object_or_404(LifeEvent, pk=pk)
    if request.method == "POST":
        event.delete()
        messages.success(request, "Life event removed.")
        return redirect("life_dashboard")
    return render(
        request,
        "life/confirm_delete.html",
        {
            "obj": event,
            "cancel_url": reverse("life_dashboard"),
        },
    )
