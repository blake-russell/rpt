from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import PersonForm
from .models import Person


@login_required
def people_dashboard(request):
    persons = Person.objects.all()
    earners = [p for p in persons if p.role in ("user", "spouse")]
    dependents = [p for p in persons if p.role == "dependent"]
    return render(
        request,
        "people/dashboard.html",
        {
            "earners": earners,
            "dependents": dependents,
        },
    )


@login_required
def person_add(request):
    form = PersonForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Person added.")
        return redirect("people_dashboard")
    return render(request, "people/person_form.html", {"form": form, "title": "Add Person"})


@login_required
def person_edit(request, pk):
    person = get_object_or_404(Person, pk=pk)
    form = PersonForm(request.POST or None, instance=person)
    if form.is_valid():
        form.save()
        messages.success(request, "Person updated.")
        return redirect("people_dashboard")
    return render(request, "people/person_form.html", {"form": form, "title": "Edit Person"})


@login_required
def person_delete(request, pk):
    person = get_object_or_404(Person, pk=pk)
    if request.method == "POST":
        person.delete()
        messages.success(request, "Person removed.")
        return redirect("people_dashboard")
    return render(
        request,
        "people/confirm_delete.html",
        {
            "obj": person,
            "cancel_url": reverse("people_dashboard"),
        },
    )
