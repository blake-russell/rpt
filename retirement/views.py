from datetime import date
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import models
from django.shortcuts import redirect, render

from debts.utils import payoff_schedule

from .engine import build_projection, derive_household_years
from .forms import PayoffScenarioForm, RetirementSettingsForm
from .models import RetirementSettings


def _payoff_vs_invest(loan, years_early, versus_return_pct):
    base_schedule = payoff_schedule(loan)
    full_interest = sum(item["interest"] for item in base_schedule)
    total_months = len(base_schedule)

    target_months = max(1, total_months - (years_early * 12))
    r = (loan.interest_rate_pct / Decimal("100")) / Decimal("12")
    p = loan.current_balance
    if r == 0:
        accelerated_payment = p / Decimal(target_months)
    else:
        accelerated_payment = (p * r) / (
            Decimal("1") - (Decimal("1") + r) ** Decimal(-target_months)
        )

    accelerated_interest = Decimal("0")
    balance = p
    for _ in range(target_months):
        if balance <= 0:
            break
        interest = (balance * r).quantize(Decimal("0.01"))
        principal = min(accelerated_payment - interest, balance)
        balance = max(balance - principal, Decimal("0"))
        accelerated_interest += interest

    interest_saved = max(full_interest - accelerated_interest, Decimal("0"))

    extra_monthly_to_invest = max(accelerated_payment - loan.monthly_payment, Decimal("0"))
    monthly_return = (versus_return_pct / Decimal("100")) / Decimal("12")
    invested_value = Decimal("0")
    for _ in range(target_months):
        invested_value = invested_value * (Decimal("1") + monthly_return) + extra_monthly_to_invest

    net_diff = interest_saved - invested_value
    return {
        "interest_saved": interest_saved.quantize(Decimal("0.01")),
        "invested_value": invested_value.quantize(Decimal("0.01")),
        "net_difference": net_diff.quantize(Decimal("0.01")),
        "accelerated_payment": accelerated_payment.quantize(Decimal("0.01")),
        "versus_return_pct": versus_return_pct,
    }


@login_required
def retirement_dashboard(request):
    settings_obj = RetirementSettings.get()

    if request.method == "POST" and request.POST.get("form_name") == "settings":
        settings_form = RetirementSettingsForm(request.POST, instance=settings_obj)
        if settings_form.is_valid():
            settings_form.save()
            messages.success(request, "Retirement settings updated.")
            return redirect("retirement_dashboard")
        messages.error(request, "Please correct the retirement settings fields.")
    else:
        settings_form = RetirementSettingsForm(instance=settings_obj)

    retirement_year, life_expectancy_year, spouse_retirement_year = derive_household_years(
        default_retirement_year=settings_obj.target_retirement_year,
        default_life_expectancy_year=settings_obj.target_life_expectancy_year,
    )

    start_year = date.today().year
    projection_rows, event_markers = build_projection(
        start_year=start_year,
        end_year=life_expectancy_year,
        retirement_year=retirement_year,
        life_expectancy_year=life_expectancy_year,
        annual_spending_today=settings_obj.annual_spending_today,
        portfolio_growth_rate_pct=settings_obj.portfolio_growth_rate_pct,
        expenses_annual_growth_pct=settings_obj.expenses_annual_growth_pct,
        ss_cola_pct=settings_obj.ss_cola_pct,
        use_budget_cashflow_for_income=settings_obj.use_budget_cashflow_for_income,
        dependent_leave_expense_reduction_pct=settings_obj.dependent_leave_expense_reduction_pct,
        withdrawal_strategy=settings_obj.withdrawal_strategy,
    )

    years = [row["year"] for row in projection_rows]
    assets = [float(row["total_assets"]) for row in projection_rows]
    debts = [float(row["total_debt"]) for row in projection_rows]
    net_worth = [float(row["net_worth"]) for row in projection_rows]

    chart_start_year = max(start_year, retirement_year - 2)
    chart_rows = [row for row in projection_rows if row["year"] >= chart_start_year]
    cashflow_years = [row["year"] for row in chart_rows]
    cashflow_income = [float(row["household_income"]) for row in chart_rows]
    cashflow_withdrawals = [float(row["total_from_assets"]) for row in chart_rows]
    cashflow_expenses = [float(row["total_expenses"]) for row in chart_rows]

    net_by_year = {row["year"]: float(row["net_worth"]) for row in projection_rows}
    marker_years = []
    marker_labels = []
    marker_values = []
    for marker in event_markers:
        year = marker["year"]
        if year in net_by_year:
            marker_years.append(year)
            marker_labels.append(marker["label"])
            marker_values.append(net_by_year[year])

    payoff_result = None
    if request.method == "POST" and request.POST.get("form_name") == "payoff":
        payoff_form = PayoffScenarioForm(request.POST)
        if payoff_form.is_valid():
            payoff_result = _payoff_vs_invest(
                payoff_form.cleaned_data["loan"],
                payoff_form.cleaned_data["years_early"],
                payoff_form.cleaned_data["versus_return_pct"],
            )
        else:
            messages.error(request, "Please correct payoff scenario inputs.")
    else:
        payoff_form = PayoffScenarioForm(
            initial={"years_early": 5, "versus_return_pct": Decimal("10.00")}
        )

    from assets.models import Account
    from budget.models import Transaction
    from debts.models import Loan as DebtLoan
    from income.models import W2Income
    from people.models import Person as IncomePerson

    hints = []
    if not IncomePerson.objects.filter(role__in=["user", "spouse"]).exists():
        hints.append(
            (
                "Income",
                "/income/",
                "No person profiles found. Add yourself (and spouse if applicable) with birth year, retirement age, and life expectancy in the Income module.",
            )
        )
    elif not W2Income.objects.filter(is_current=True).exists():
        hints.append(
            (
                "Income",
                "/income/",
                "No current income found. Add W2 income entries in the Income module for accurate projections.",
            )
        )
    if not Account.objects.exists():
        hints.append(
            (
                "Assets",
                "/assets/",
                "No investment accounts found. Add your 401k, IRA, brokerage, and other accounts in the Assets module.",
            )
        )
    if not DebtLoan.objects.filter(is_active=True).exists():
        hints.append(
            (
                "Debts",
                "/debts/",
                "No active loans found. If you have a mortgage, car loans, or student loans, add them in the Debts module so debt service is properly accounted for.",
            )
        )
    if not Transaction.objects.filter(is_excluded=False).exists():
        hints.append(
            (
                "Budget",
                "/budget/",
                "No budget transactions found. Import your bank CSVs in the Budget module to enable automatic expense baseline calculations.",
            )
        )

    earner_profiles_check = list(IncomePerson.objects.filter(role__in=["user", "spouse"]))
    derived_info = []
    for p in earner_profiles_check:
        if p.birth_year and p.retirement_age:
            derived_info.append(f"{p.name}: retires {p.birth_year + p.retirement_age}")
        if p.life_expectancy_year:
            derived_info.append(f"{p.name}: life expectancy {p.life_expectancy_year}")

    # Year-cell tooltip: pre-compute "Name — age X" for each projection year
    all_persons = list(
        IncomePerson.objects.all().order_by(
            models.Case(
                models.When(role="user", then=0),
                models.When(role="spouse", then=1),
                default=2,
                output_field=models.IntegerField(),
            ),
            "name",
        )
    )
    persons_with_birth = [(p.name, p.birth_year) for p in all_persons if p.birth_year]
    for row in projection_rows:
        yr = row["year"]
        lines = [f"{name} — age {yr - birth_yr}" for name, birth_yr in persons_with_birth]
        row["year_tooltip"] = "&#10;".join(lines) if lines else ""

    return render(
        request,
        "retirement/dashboard.html",
        {
            "settings_form": settings_form,
            "payoff_form": payoff_form,
            "payoff_result": payoff_result,
            "projection_rows": projection_rows,
            "retirement_year": retirement_year,
            "spouse_retirement_year": spouse_retirement_year or -1,
            "life_expectancy_year": life_expectancy_year,
            "chart_years": years,
            "chart_assets": assets,
            "chart_debts": debts,
            "chart_net_worth": net_worth,
            "cashflow_years": cashflow_years,
            "cashflow_income": cashflow_income,
            "cashflow_withdrawals": cashflow_withdrawals,
            "cashflow_expenses": cashflow_expenses,
            "event_markers": event_markers,
            "hints": hints,
            "derived_info": derived_info,
        },
    )
