from datetime import date
from decimal import Decimal

from assets.models import Account
from budget.utils import monthly_cashflow_summary
from debts.models import Loan
from debts.utils import project_balance
from income.models import SocialSecurity
from income.utils import project_income
from life.models import LifeEvent
from people.models import Person

# ── Account tax classification ────────────────────────────────────────────────
# Taxable accounts: gains taxed each year, withdrawals at capital gains rates.
# (For simplicity we treat as ordinary income — capital gains not modeled yet.)
TAXABLE_ACCOUNT_TYPES = {"brokerage", "crypto", "other"}
# Tax-deferred: contributions pre-tax; withdrawals taxed as ordinary income.
TAX_DEFERRED_ACCOUNT_TYPES = {"ira", "401k"}
# Post-tax (Roth): contributions already taxed; withdrawals are tax-free.
POST_TAX_ACCOUNT_TYPES = {"roth_ira", "roth_401k"}

# ── Withdrawal strategies ─────────────────────────────────────────────────────
# 'traditional'   — taxable first → tax-deferred → Roth last (grow tax-advantaged longest)
# 'proportional'  — withdraw from each bucket proportional to its share of total assets

# ── 2025 Social Security Taxation Thresholds (IRS Publication 915) ───────────
# Combined income = AGI + 0.5 × SS benefits + tax-exempt interest.
# Thresholds are NOT inflation-adjusted (statutory since 1983/1994).
SS_TAX_THRESHOLDS = {
    "single": {"tier1": Decimal("25000"), "tier2": Decimal("34000")},
    "married": {"tier1": Decimal("32000"), "tier2": Decimal("44000")},
}
SS_TIER1_TAXABLE_PCT = Decimal("0.50")
SS_MAX_TAXABLE_PCT = Decimal("0.85")

# ── 2025 Federal Income Tax Brackets (IRS Rev. Proc. 2024-40) ────────────────
# Applies to ordinary income: wages, traditional IRA/401k withdrawals, taxable SS.
# Format: (lower_bound, upper_bound_or_None, rate)
FEDERAL_TAX_BRACKETS = {
    "single": [
        (Decimal("0"), Decimal("11925"), Decimal("0.10")),
        (Decimal("11925"), Decimal("48475"), Decimal("0.12")),
        (Decimal("48475"), Decimal("103350"), Decimal("0.22")),
        (Decimal("103350"), Decimal("197300"), Decimal("0.24")),
        (Decimal("197300"), Decimal("250525"), Decimal("0.32")),
        (Decimal("250525"), Decimal("626350"), Decimal("0.35")),
        (Decimal("626350"), None, Decimal("0.37")),
    ],
    "married": [
        (Decimal("0"), Decimal("23850"), Decimal("0.10")),
        (Decimal("23850"), Decimal("96950"), Decimal("0.12")),
        (Decimal("96950"), Decimal("206700"), Decimal("0.22")),
        (Decimal("206700"), Decimal("394600"), Decimal("0.24")),
        (Decimal("394600"), Decimal("501050"), Decimal("0.32")),
        (Decimal("501050"), Decimal("751600"), Decimal("0.35")),
        (Decimal("751600"), None, Decimal("0.37")),
    ],
}
# 2025 standard deduction (reduces taxable income before bracket calculation)
STANDARD_DEDUCTION = {
    "single": Decimal("15000"),
    "married": Decimal("30000"),
}


def _year_end(year):
    return date(year, 12, 31)


def _to_decimal(value):
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _taxable_ss_amount(ss_income, agi, filing_status):
    """IRS Publication 915: determine the taxable portion of SS benefits."""
    if ss_income <= 0:
        return Decimal("0")
    thresholds = SS_TAX_THRESHOLDS[filing_status]
    combined = agi + ss_income * Decimal("0.5")
    if combined <= thresholds["tier1"]:
        return Decimal("0")
    elif combined <= thresholds["tier2"]:
        excess = combined - thresholds["tier1"]
        return min(ss_income * SS_TIER1_TAXABLE_PCT, excess * SS_TIER1_TAXABLE_PCT)
    else:
        tier1_taxable = (thresholds["tier2"] - thresholds["tier1"]) * SS_TIER1_TAXABLE_PCT
        tier2_taxable = (combined - thresholds["tier2"]) * SS_MAX_TAXABLE_PCT
        return min(ss_income * SS_MAX_TAXABLE_PCT, tier1_taxable + tier2_taxable)


def _federal_income_tax(taxable_income, filing_status):
    """Progressive federal income tax (net of standard deduction)."""
    if taxable_income <= 0:
        return Decimal("0")
    brackets = FEDERAL_TAX_BRACKETS[filing_status]
    tax = Decimal("0")
    for lower, upper, rate in brackets:
        if taxable_income <= lower:
            break
        bracket_income = (
            min(taxable_income, upper) if upper is not None else taxable_income
        ) - lower
        tax += bracket_income * rate
    return tax


def _withdraw_traditional(shortfall, taxable_val, deferred_val, roth_val):
    """
    Traditional sequence: taxable → tax-deferred → Roth.
    Returns (taxable_withdrawal, deferred_withdrawal, roth_withdrawal).
    """
    taxable_wd = min(shortfall, max(taxable_val, Decimal("0")))
    rem1 = shortfall - taxable_wd
    deferred_wd = min(rem1, max(deferred_val, Decimal("0")))
    rem2 = rem1 - deferred_wd
    roth_wd = min(rem2, max(roth_val, Decimal("0")))
    return taxable_wd, deferred_wd, roth_wd


def _withdraw_proportional(shortfall, taxable_val, deferred_val, roth_val):
    """
    Proportional: draw from each bucket relative to its share of total assets.
    Smoother tax bill, lower lifetime taxes.
    """
    tv, dv, rv = (
        max(taxable_val, Decimal("0")),
        max(deferred_val, Decimal("0")),
        max(roth_val, Decimal("0")),
    )
    total = tv + dv + rv
    if total == 0:
        return Decimal("0"), Decimal("0"), Decimal("0")
    taxable_wd = min(shortfall * (tv / total), tv)
    deferred_wd = min(shortfall * (dv / total), dv)
    roth_wd = min(shortfall * (rv / total), rv)
    # Distribute any rounding remainder via traditional fallback
    drawn = taxable_wd + deferred_wd + roth_wd
    rem = shortfall - drawn
    if rem > 0:
        extra_t, extra_d, extra_r = _withdraw_traditional(
            rem, tv - taxable_wd, dv - deferred_wd, rv - roth_wd
        )
        taxable_wd += extra_t
        deferred_wd += extra_d
        roth_wd += extra_r
    return taxable_wd, deferred_wd, roth_wd


def _person_retirement_year(person, default_retirement_year):
    if person.birth_year and person.retirement_age:
        return person.birth_year + person.retirement_age
    return default_retirement_year


def _person_life_expectancy_year(person):
    return person.life_expectancy_year


def derive_household_years(default_retirement_year, default_life_expectancy_year):
    earners = Person.objects.filter(role__in=["user", "spouse"])

    derived_retirement = []
    derived_life_expectancy = []
    for person in earners:
        if person.birth_year and person.retirement_age:
            derived_retirement.append(person.birth_year + person.retirement_age)
        if person.life_expectancy_year:
            derived_life_expectancy.append(person.life_expectancy_year)

    retirement_year = min(derived_retirement) if derived_retirement else default_retirement_year
    life_expectancy_year = (
        max(derived_life_expectancy) if derived_life_expectancy else default_life_expectancy_year
    )

    spouse_retirement_year = None
    if len(derived_retirement) > 1:
        spouse_retirement_year = max(derived_retirement)

    return retirement_year, life_expectancy_year, spouse_retirement_year


def _social_security_by_year(start_year, end_year, ss_cola_pct):
    """Return dict year -> total SS income, with COLA growth applied each year after claim."""
    result = {year: Decimal("0") for year in range(start_year, end_year + 1)}
    cola = _to_decimal(ss_cola_pct) / Decimal("100")
    for ss in SocialSecurity.objects.select_related("person").all():
        claim_year = ss.planned_claim_year
        base_benefit = _to_decimal(ss.annual_benefit)
        if not claim_year or base_benefit <= 0:
            continue
        person_le_year = _person_life_expectancy_year(ss.person)
        for year in range(max(start_year, claim_year), end_year + 1):
            if person_le_year and year > person_le_year:
                break
            years_since_claim = year - claim_year
            inflated_benefit = base_benefit * ((Decimal("1") + cola) ** years_since_claim)
            result[year] += inflated_benefit
    return result


def _dependent_moveout_years():
    """Returns list of (year, name) tuples for dependents with known move-out year."""
    result = []
    for dep in Person.objects.filter(role="dependent"):
        if dep.birth_year and dep.move_out_age:
            result.append((dep.birth_year + dep.move_out_age, dep.name))
    return sorted(result, key=lambda x: x[0])


def _event_markers(primary_retirement_year):
    markers = []

    for event in LifeEvent.objects.select_related("dependent", "person").all():
        if event.event_year:
            label = f"Life: {event.owner_name} {event.get_event_type_display()}"
            markers.append({"year": event.event_year, "label": label})

    for loan in Loan.objects.filter(is_active=True):
        markers.append(
            {"year": loan.maturity_date.year, "label": f"Loan payoff: {loan.description}"}
        )

    markers.append({"year": primary_retirement_year, "label": "Household retirement starts"})
    markers.sort(key=lambda m: m["year"])
    return markers


def _earner_profiles(start_year, end_year, default_retirement_year):
    earners = list(Person.objects.filter(role__in=["user", "spouse"]))
    profiles = []

    current_income_by_person = {}
    total_current_income = Decimal("0")

    for person in earners:
        projection = project_income(person, start_year, end_year)
        current_income = _to_decimal(projection.get(start_year, Decimal("0")))
        current_income_by_person[person.pk] = current_income
        total_current_income += current_income

    for person in earners:
        merit_raise = person.raise_schedules.filter(raise_type="annual_pct").first()
        annual_merit_pct = (
            _to_decimal(merit_raise.annual_pct)
            if merit_raise and merit_raise.annual_pct is not None
            else Decimal("0")
        )

        if total_current_income > 0:
            income_share = current_income_by_person[person.pk] / total_current_income
        elif earners:
            income_share = Decimal("1") / Decimal(len(earners))
        else:
            income_share = Decimal("0")

        profiles.append(
            {
                "person": person,
                "retirement_year": _person_retirement_year(person, default_retirement_year),
                "income_projection": projection,
                "income_share": income_share,
                "annual_merit_pct": annual_merit_pct,
            }
        )

    return profiles


def build_projection(
    start_year,
    end_year,
    retirement_year,
    life_expectancy_year,
    annual_spending_today,
    portfolio_growth_rate_pct,
    expenses_annual_growth_pct,
    ss_cola_pct=Decimal("2.50"),
    use_budget_cashflow_for_income=True,
    dependent_leave_expense_reduction_pct=Decimal("0"),
    withdrawal_strategy="traditional",
    healthcare_inflation_pct=Decimal("4.50"),
):
    inflation_rate = _to_decimal(expenses_annual_growth_pct)
    projection_end = min(end_year, life_expectancy_year)

    earner_profiles = _earner_profiles(start_year, projection_end, retirement_year)

    social_security_by_year = _social_security_by_year(start_year, projection_end, ss_cola_pct)

    life_cost_map = {}
    life_event_details_map = {}  # year -> list of {label, amount}
    cpi_rate = inflation_rate / Decimal("100")
    for event in LifeEvent.objects.select_related("dependent", "person").all():
        if not event.event_year or not event.estimated_cost:
            continue
        label = f"{event.owner_name} — {event.get_event_type_display()}"
        cost_today = _to_decimal(event.estimated_cost)
        if event.is_annual:
            # Each occurrence is inflated to its own year (costs rise with CPI each year)
            for yr in range(event.event_year, projection_end + 1):
                years_out = max(0, yr - start_year)
                inflated = cost_today * ((Decimal("1") + cpi_rate) ** years_out)
                life_cost_map[yr] = life_cost_map.get(yr, Decimal("0")) + inflated
                life_event_details_map.setdefault(yr, []).append(
                    {
                        "label": label + " (annual)",
                        "amount": float(inflated),
                    }
                )
        else:
            years_out = max(0, event.event_year - start_year)
            inflated = cost_today * ((Decimal("1") + cpi_rate) ** years_out)
            life_cost_map[event.event_year] = (
                life_cost_map.get(event.event_year, Decimal("0")) + inflated
            )
            life_event_details_map.setdefault(event.event_year, []).append(
                {
                    "label": label,
                    "amount": float(inflated),
                }
            )

    # Budget baseline: exclude categories marked as debt service for retirement-expense realism.
    cashflow = monthly_cashflow_summary(exclude_debt_service=True)
    rolling_income_annual = _to_decimal(cashflow["rolling_avg_income"]) * Decimal("12")
    rolling_expenses_annual = _to_decimal(cashflow["rolling_avg_expenses"]) * Decimal("12")
    rolling_healthcare_annual = _to_decimal(cashflow["rolling_avg_healthcare_expenses"]) * Decimal(
        "12"
    )

    # Pre-compute base spending split for the projection loop
    base_spending = _to_decimal(annual_spending_today)
    if use_budget_cashflow_for_income and rolling_expenses_annual > 0:
        base_spending = rolling_expenses_annual
    elif base_spending == Decimal("0"):
        base_spending = rolling_expenses_annual
    base_healthcare = (
        rolling_healthcare_annual
        if (use_budget_cashflow_for_income and rolling_expenses_annual > 0)
        else Decimal("0")
    )
    base_regular = max(base_spending - base_healthcare, Decimal("0"))
    healthcare_rate = _to_decimal(healthcare_inflation_pct) / Decimal("100")

    # Split assets into three tax buckets
    taxable_assets = Decimal("0")  # brokerage, crypto, other
    deferred_assets = Decimal("0")  # traditional IRA, 401k
    roth_assets = Decimal("0")  # Roth IRA, Roth 401k
    taxable_contrib_monthly = Decimal("0")
    deferred_contrib_monthly = Decimal("0")
    roth_contrib_monthly = Decimal("0")
    for acct in Account.objects.prefetch_related("holdings__contributions").all():
        acct_val = _to_decimal(
            acct.total_value if acct.total_value is not None else acct.total_cost_basis
        )
        contrib = _to_decimal(acct.monthly_contribution_total)
        if acct.account_type in POST_TAX_ACCOUNT_TYPES:
            roth_assets += acct_val
            roth_contrib_monthly += contrib
        elif acct.account_type in TAX_DEFERRED_ACCOUNT_TYPES:
            deferred_assets += acct_val
            deferred_contrib_monthly += contrib
        else:
            taxable_assets += acct_val
            taxable_contrib_monthly += contrib

    # Determine filing status once (used for SS tax and income tax)
    has_spouse = Person.objects.filter(role="spouse").exists()
    filing_status = "married" if has_spouse else "single"

    # Non-primary real estate is always included in illiquid assets (investment properties).
    # Primary residence equity is excluded from retirement asset totals.
    mortgage_loans = list(
        Loan.objects.filter(is_active=True, loan_type="mortgage", is_primary_residence=False)
    )
    base_home_values = {
        loan.pk: _to_decimal(loan.property_estimated_value) for loan in mortgage_loans
    }

    growth_rate = _to_decimal(portfolio_growth_rate_pct) / Decimal("100")
    taxable_yearly_contrib = taxable_contrib_monthly * Decimal("12")
    deferred_yearly_contrib = deferred_contrib_monthly * Decimal("12")
    roth_yearly_contrib = roth_contrib_monthly * Decimal("12")

    event_markers = _event_markers(retirement_year)
    dependent_moveout_years = _dependent_moveout_years()  # list of (year, name)
    dep_reduction = _to_decimal(dependent_leave_expense_reduction_pct) / Decimal("100")
    prev_debt_service_per_loan = {}  # loan.pk -> last known annual debt service

    rows = []
    taxable_value = taxable_assets
    deferred_value = deferred_assets
    roth_value = roth_assets

    for year in range(start_year, projection_end + 1):
        years_from_start = year - start_year

        household_income = Decimal("0")
        active_income_share = Decimal("0")
        for profile in earner_profiles:
            if year >= profile["retirement_year"]:
                continue

            active_income_share += profile["income_share"]
            if use_budget_cashflow_for_income:
                person_base = rolling_income_annual * profile["income_share"]
                person_income = person_base * (
                    (Decimal("1") + (profile["annual_merit_pct"] / Decimal("100")))
                    ** years_from_start
                )
            else:
                person_income = _to_decimal(profile["income_projection"].get(year, Decimal("0")))
            household_income += person_income

        household_income += social_security_by_year.get(year, Decimal("0"))
        ss_income_this_year = social_security_by_year.get(year, Decimal("0"))

        # Assets grow; contributions taper as earners retire.
        taxable_value = taxable_value * (Decimal("1") + growth_rate)
        deferred_value = deferred_value * (Decimal("1") + growth_rate)
        roth_value = roth_value * (Decimal("1") + growth_rate)
        taxable_value += taxable_yearly_contrib * active_income_share
        deferred_value += deferred_yearly_contrib * active_income_share
        roth_value += roth_yearly_contrib * active_income_share

        # Consumer expenses: healthcare bucket inflated at healthcare_inflation_pct,
        # remaining non-debt expenses inflated at CPI (expenses_annual_growth_pct).
        healthcare_expenses = base_healthcare * (
            (Decimal("1") + healthcare_rate) ** years_from_start
        )
        regular_expenses = base_regular * ((Decimal("1") + cpi_rate) ** years_from_start)
        consumer_expenses = healthcare_expenses + regular_expenses

        moveout_hits = sum(1 for (y, _name) in dependent_moveout_years if y <= year)
        moveout_this_year = [(y, name) for (y, name) in dependent_moveout_years if y == year]
        if moveout_hits and dep_reduction > 0:
            reduction_factor = max(Decimal("0"), Decimal("1") - (dep_reduction * moveout_hits))
            consumer_expenses *= reduction_factor

        # Debt service: calculated dynamically per year, falls off when loans are paid
        # Escrowed costs (insurance/taxes) are ALWAYS consumer expenses, not debt service
        debt_service_annual = Decimal("0")
        escrowed_costs_annual = Decimal("0")
        debt_payoff_names = []  # loans that paid off THIS year

        for loan in Loan.objects.filter(is_active=True):
            balance = _to_decimal(project_balance(loan, _year_end(year)))
            prev_service = prev_debt_service_per_loan.get(loan.pk, None)

            # Insurance and taxes are ALWAYS consumer expenses (whether loan active or not)
            if loan.is_escrowed:
                if loan.homeowners_insurance_yearly:
                    escrowed_costs_annual += _to_decimal(loan.homeowners_insurance_yearly)
                if loan.real_estate_tax_yearly:
                    escrowed_costs_annual += _to_decimal(loan.real_estate_tax_yearly)
            if loan.car_insurance_yearly:
                escrowed_costs_annual += _to_decimal(loan.car_insurance_yearly)

            if balance > 0:
                loan_service = _to_decimal(loan.monthly_payment) * Decimal("12")
                debt_service_annual += loan_service
                prev_debt_service_per_loan[loan.pk] = loan_service
            else:
                # Loan just paid off if it had a positive service last year
                if prev_service is not None and prev_service > 0:
                    debt_payoff_names.append(loan.description or f"Loan #{loan.pk}")
                prev_debt_service_per_loan[loan.pk] = Decimal("0")

        # Add escrowed costs to consumer expenses (they're ongoing, not debt service)
        consumer_expenses += escrowed_costs_annual

        # Total expenses = consumer + debt + life events
        total_expenses = consumer_expenses + debt_service_annual

        life_events_cost = life_cost_map.get(year, Decimal("0"))
        if life_events_cost:
            total_expenses += life_events_cost

        # Build rich tooltip details for this year's expenses
        year_event_details = list(life_event_details_map.get(year, []))
        for _y, dep_name in moveout_this_year:
            pct = float(dep_reduction * 100)
            year_event_details.append(
                {"label": f"{dep_name} moves out (−{pct:.0f}% consumer expenses)", "amount": None}
            )

        # ── Withdrawal strategy ──────────────────────────────────────────────
        shortfall = max(total_expenses - household_income, Decimal("0"))
        if withdrawal_strategy == "proportional":
            taxable_wd, deferred_wd, roth_wd = _withdraw_proportional(
                shortfall, taxable_value, deferred_value, roth_value
            )
        else:  # 'traditional' (default)
            taxable_wd, deferred_wd, roth_wd = _withdraw_traditional(
                shortfall, taxable_value, deferred_value, roth_value
            )
        taxable_value -= taxable_wd
        deferred_value -= deferred_wd
        roth_value -= roth_wd
        pre_tax_withdrawal = taxable_wd + deferred_wd
        post_tax_withdrawal = roth_wd
        required_withdrawals = pre_tax_withdrawal + post_tax_withdrawal
        # Detect true shortfall: couldn't cover full expense gap from any bucket
        unmet_shortfall = shortfall - required_withdrawals
        is_shortfall = unmet_shortfall > Decimal("0.01")

        # ── Federal income tax on pre-tax withdrawals + taxable SS ───────────
        taxable_ss = _taxable_ss_amount(
            ss_income_this_year, agi=pre_tax_withdrawal, filing_status=filing_status
        )
        gross_taxable = pre_tax_withdrawal + taxable_ss
        net_taxable = max(gross_taxable - STANDARD_DEDUCTION[filing_status], Decimal("0"))
        income_tax = _federal_income_tax(net_taxable, filing_status)
        # Deduct only what can actually be paid from remaining assets
        actual_tax_t = min(income_tax, max(taxable_value, Decimal("0")))
        taxable_value -= actual_tax_t
        rem_tax = income_tax - actual_tax_t
        actual_tax_d = min(rem_tax, max(deferred_value, Decimal("0")))
        deferred_value -= actual_tax_d
        rem_tax2 = rem_tax - actual_tax_d
        actual_tax_r = min(rem_tax2, max(roth_value, Decimal("0")))
        roth_value -= actual_tax_r
        actual_income_tax = actual_tax_t + actual_tax_d + actual_tax_r
        total_expenses += actual_income_tax
        # Total pulled from assets = expense withdrawals + actual tax paid
        total_from_assets = required_withdrawals + actual_income_tax

        total_debt = Decimal("0")
        for loan in Loan.objects.filter(is_active=True):
            total_debt += _to_decimal(project_balance(loan, _year_end(year)))

        illiquid_assets = Decimal("0")
        for loan in mortgage_loans:
            start_value = base_home_values.get(loan.pk, Decimal("0"))
            if start_value <= 0:
                continue
            home_growth = _to_decimal(loan.expected_home_value_growth_pct) / Decimal("100")
            current_home_value = start_value * ((Decimal("1") + home_growth) ** years_from_start)
            mortgage_balance = _to_decimal(project_balance(loan, _year_end(year)))
            illiquid_assets += max(current_home_value - mortgage_balance, Decimal("0"))

        liquid_assets_value = taxable_value + deferred_value + roth_value
        total_assets = liquid_assets_value + illiquid_assets
        net_worth = total_assets - total_debt

        rows.append(
            {
                "year": year,
                "household_income": household_income.quantize(Decimal("0.01")),
                "ss_income": ss_income_this_year.quantize(Decimal("0.01")),
                "total_assets": total_assets.quantize(Decimal("0.01")),
                "taxable_assets": max(taxable_value, Decimal("0")).quantize(Decimal("0.01")),
                "deferred_assets": max(deferred_value, Decimal("0")).quantize(Decimal("0.01")),
                "roth_assets": max(roth_value, Decimal("0")).quantize(Decimal("0.01")),
                "pre_tax_assets": (
                    max(taxable_value, Decimal("0")) + max(deferred_value, Decimal("0"))
                ).quantize(Decimal("0.01")),
                "post_tax_assets": max(roth_value, Decimal("0")).quantize(Decimal("0.01")),
                "total_debt": total_debt.quantize(Decimal("0.01")),
                "life_events_cost": life_events_cost.quantize(Decimal("0.01")),
                "life_event_details": year_event_details,
                "debt_payoff_names": debt_payoff_names,
                "total_expenses": total_expenses.quantize(Decimal("0.01")),
                "consumer_expenses": consumer_expenses.quantize(Decimal("0.01")),
                "escrowed_costs": escrowed_costs_annual.quantize(Decimal("0.01")),
                "debt_service": debt_service_annual.quantize(Decimal("0.01")),
                "income_tax": actual_income_tax.quantize(Decimal("0.01")),
                "income_tax_owed": income_tax.quantize(Decimal("0.01")),
                "taxable_ss": taxable_ss.quantize(Decimal("0.01")),
                "pre_tax_withdrawal": pre_tax_withdrawal.quantize(Decimal("0.01")),
                "post_tax_withdrawal": post_tax_withdrawal.quantize(Decimal("0.01")),
                "required_withdrawals": required_withdrawals.quantize(Decimal("0.01")),
                "total_from_assets": total_from_assets.quantize(Decimal("0.01")),
                "net_worth": net_worth.quantize(Decimal("0.01")),
                "illiquid_assets": illiquid_assets.quantize(Decimal("0.01")),
                "is_shortfall": is_shortfall,
            }
        )

    return rows, event_markers
