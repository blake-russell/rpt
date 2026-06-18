from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from people.models import Person

from .forms import BonusForm, RaiseScheduleForm, SocialSecurityForm, W2IncomeForm
from .models import Bonus, RaiseSchedule, SocialSecurity, W2Income


@login_required
def income_dashboard(request):
    persons = Person.objects.prefetch_related("w2_incomes__bonuses", "raise_schedules").all()

    earners = [p for p in persons if p.role in ("user", "spouse")]
    dependents = [p for p in persons if p.role == "dependent"]

    total_salary = Decimal("0")
    total_bonus = Decimal("0")
    for person in earners:
        for w2 in person.w2_incomes.filter(is_current=True):
            total_salary += w2.annual_salary
            for bonus in w2.bonuses.all():
                total_bonus += bonus.resolved_amount()

    context = {
        "earners": earners,
        "dependents": dependents,
        "total_salary": total_salary,
        "total_bonus": total_bonus,
        "total_income": total_salary + total_bonus,
    }
    return render(request, "income/dashboard.html", context)


# ── W2 Income ─────────────────────────────────────────────────────────────────


def _save_w2_inline_fields(form, w2):
    """
    After saving a W2 instance, create/update the inline bonus and merit raise
    fields that were submitted with the W2 form.
    """
    bonus_type = form.cleaned_data.get("bonus_type")
    bonus_amount = form.cleaned_data.get("bonus_amount")
    bonus_description = form.cleaned_data.get("bonus_description") or ""
    annual_merit_pct = form.cleaned_data.get("annual_merit_pct")

    # Bonus — replace existing (one bonus per W2 via this form)
    existing_bonus = w2.bonuses.first()
    if bonus_type and bonus_amount is not None:
        if existing_bonus:
            existing_bonus.bonus_type = bonus_type
            existing_bonus.amount = bonus_amount
            existing_bonus.description = bonus_description
            existing_bonus.save()
        else:
            Bonus.objects.create(
                w2=w2,
                bonus_type=bonus_type,
                amount=bonus_amount,
                description=bonus_description,
            )
    elif existing_bonus:
        existing_bonus.delete()

    # Merit raise — one annual_pct raise schedule per person
    if annual_merit_pct is not None:
        RaiseSchedule.objects.update_or_create(
            person=w2.person,
            raise_type="annual_pct",
            defaults={"annual_pct": annual_merit_pct},
        )


@login_required
def w2_add(request):
    form = W2IncomeForm(request.POST or None)
    if form.is_valid():
        w2 = form.save()
        _save_w2_inline_fields(form, w2)
        messages.success(request, "W2 income added.")
        return redirect("income_dashboard")
    return render(request, "income/w2_form.html", {"form": form, "title": "Add W2 Income"})


@login_required
def w2_edit(request, pk):
    w2 = get_object_or_404(W2Income, pk=pk)
    form = W2IncomeForm(request.POST or None, instance=w2)
    if form.is_valid():
        w2 = form.save()
        _save_w2_inline_fields(form, w2)
        messages.success(request, "W2 income updated.")
        return redirect("income_dashboard")
    return render(request, "income/w2_form.html", {"form": form, "title": "Edit W2 Income"})


@login_required
def w2_delete(request, pk):
    w2 = get_object_or_404(W2Income, pk=pk)
    if request.method == "POST":
        w2.delete()
        messages.success(request, "W2 entry removed.")
        return redirect("income_dashboard")
    return render(
        request,
        "income/confirm_delete.html",
        {"obj": w2, "cancel_url": reverse("income_dashboard")},
    )


# ── Bonus ─────────────────────────────────────────────────────────────────────


@login_required
def bonus_add(request):
    initial = {}
    w2_id = request.GET.get("w2")
    if w2_id:
        initial["w2"] = w2_id
    form = BonusForm(request.POST or None, initial=initial)
    if form.is_valid():
        form.save()
        messages.success(request, "Bonus added.")
        return redirect("income_dashboard")
    return render(request, "income/bonus_form.html", {"form": form, "title": "Add Bonus"})


@login_required
def bonus_delete(request, pk):
    bonus = get_object_or_404(Bonus, pk=pk)
    if request.method == "POST":
        bonus.delete()
        messages.success(request, "Bonus removed.")
        return redirect("income_dashboard")
    return render(
        request,
        "income/confirm_delete.html",
        {"obj": bonus, "cancel_url": reverse("income_dashboard")},
    )


# ── Raise Schedule ────────────────────────────────────────────────────────────


@login_required
def raise_add(request):
    initial = {}
    person_id = request.GET.get("person")
    if person_id:
        initial["person"] = person_id
    form = RaiseScheduleForm(request.POST or None, initial=initial)
    if form.is_valid():
        form.save()
        messages.success(request, "Raise schedule added.")
        return redirect("income_dashboard")
    return render(request, "income/raise_form.html", {"form": form, "title": "Add Raise Schedule"})


@login_required
def raise_delete(request, pk):
    rs = get_object_or_404(RaiseSchedule, pk=pk)
    if request.method == "POST":
        rs.delete()
        messages.success(request, "Raise schedule removed.")
        return redirect("income_dashboard")
    return render(
        request,
        "income/confirm_delete.html",
        {"obj": rs, "cancel_url": reverse("income_dashboard")},
    )


# ── Social Security ───────────────────────────────────────────────────────────


@login_required
def ss_edit(request, person_pk):
    """Add or update Social Security estimates for a person (upsert via OneToOne)."""
    person = get_object_or_404(Person, pk=person_pk, role__in=["user", "spouse"])
    instance, _ = SocialSecurity.objects.get_or_create(person=person)
    form = SocialSecurityForm(request.POST or None, instance=instance)
    # Lock the person field to the URL-specified person
    form.fields["person"].initial = person.pk
    form.fields["person"].disabled = True
    if form.is_valid():
        form.save()
        messages.success(request, f"Social Security info saved for {person.name}.")
        return redirect("income_dashboard")
    return render(
        request,
        "income/ss_form.html",
        {
            "form": form,
            "person": person,
            "title": f"Social Security — {person.name}",
        },
    )


@login_required
def ss_delete(request, person_pk):
    person = get_object_or_404(Person, pk=person_pk)
    ss = get_object_or_404(SocialSecurity, person=person)
    if request.method == "POST":
        ss.delete()
        messages.success(request, "Social Security info removed.")
        return redirect("income_dashboard")
    return render(
        request,
        "income/confirm_delete.html",
        {"obj": ss, "cancel_url": reverse("income_dashboard")},
    )
