from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .forms import AppSettingsForm
from .models import AppSettings


@login_required
def dashboard(request):
    from assets.models import Account
    from debts.models import Loan
    from income.models import W2Income

    total_salary, total_bonus = Decimal("0"), Decimal("0")
    for w2 in W2Income.objects.filter(is_current=True).prefetch_related("bonuses"):
        total_salary += w2.annual_salary
        for bonus in w2.bonuses.all():
            total_bonus += bonus.resolved_amount()

    total_assets = Decimal("0")
    has_assets = False
    for acct in Account.objects.prefetch_related("holdings").all():
        v = acct.total_value
        if v is not None:
            total_assets += v
            has_assets = True

    # Include non-primary real estate equity in investable assets.
    # Primary residence equity is shown separately but not included in investable total.
    total_real_estate_equity = Decimal("0")
    primary_residence_equity = Decimal("0")
    for loan in Loan.objects.filter(is_active=True, loan_type="mortgage"):
        if loan.equity is not None:
            if loan.is_primary_residence:
                primary_residence_equity += loan.equity
            else:
                total_real_estate_equity += loan.equity
                has_assets = True
    total_assets += total_real_estate_equity

    total_debt = sum(loan.current_balance for loan in Loan.objects.filter(is_active=True))

    return render(
        request,
        "core/dashboard.html",
        {
            "total_income": total_salary + total_bonus,
            "total_assets": total_assets if has_assets else None,
            "total_real_estate_equity": total_real_estate_equity,
            "primary_residence_equity": primary_residence_equity,
            "total_debt": total_debt,
            "net_worth": (total_assets - total_debt) if has_assets else None,
        },
    )


@login_required
def settings_view(request):
    instance = AppSettings.get()
    if request.method == "POST":
        form = AppSettingsForm(request.POST, instance=instance)
        if form.is_valid():
            form.save()
            if request.htmx:
                return render(request, "core/partials/settings_toast.html")
            messages.success(request, "Settings saved.")
            return redirect("settings")
    else:
        form = AppSettingsForm(instance=instance)
    return render(request, "core/settings.html", {"form": form})
