from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from .forms import DebtInfoForm, LoanForm
from .models import DebtInfo, Loan
from .utils import payoff_schedule


@login_required
def debts_dashboard(request):
    loans = Loan.objects.filter(is_active=True)
    total_debt = sum(loan.current_balance for loan in loans)
    total_equity = sum(loan.equity for loan in loans if loan.equity is not None)
    debt_info = DebtInfo.get()

    grouped = {}
    for lt, label in Loan.LOAN_TYPES:
        group = [loan for loan in loans if loan.loan_type == lt]
        if group:
            grouped[label] = group

    return render(
        request,
        "debts/dashboard.html",
        {
            "grouped": grouped,
            "total_debt": total_debt,
            "total_equity": total_equity,
            "debt_info_form": DebtInfoForm(instance=debt_info),
            "debt_info": debt_info,
        },
    )


@login_required
@require_POST
def debt_info_save(request):
    debt_info = DebtInfo.get()
    form = DebtInfoForm(request.POST, instance=debt_info)
    if form.is_valid():
        form.save()
        messages.success(request, "Debt informational amounts updated.")
    else:
        messages.error(request, "Please correct the debt informational fields and try again.")
    return redirect("debts_dashboard")


@login_required
def loan_add(request):
    form = LoanForm(request.POST or None)
    if form.is_valid():
        form.save()
        messages.success(request, "Loan added.")
        return redirect("debts_dashboard")
    return render(request, "debts/loan_form.html", {"form": form, "title": "Add Loan"})


@login_required
def loan_edit(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    form = LoanForm(request.POST or None, instance=loan)
    if form.is_valid():
        form.save()
        messages.success(request, "Loan updated.")
        return redirect("debts_dashboard")
    return render(
        request, "debts/loan_form.html", {"form": form, "title": f"Edit — {loan.description}"}
    )


@login_required
def loan_delete(request, pk):
    loan = get_object_or_404(Loan, pk=pk)
    if request.method == "POST":
        loan.delete()
        messages.success(request, "Loan removed.")
        return redirect("debts_dashboard")
    return render(
        request,
        "debts/confirm_delete.html",
        {
            "obj": loan,
            "cancel_url": reverse("debts_dashboard"),
        },
    )


@login_required
def loan_amortization(request, pk):
    """HTMX endpoint — returns amortization table partial for a single loan."""
    loan = get_object_or_404(Loan, pk=pk)
    schedule = payoff_schedule(loan)
    return render(
        request,
        "debts/partials/amortization_table.html",
        {
            "loan": loan,
            "schedule": schedule,
        },
    )
