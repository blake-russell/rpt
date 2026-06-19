from decimal import Decimal

from .models import Transaction


def monthly_cashflow_summary(queryset=None, exclude_debt_service=False):
    """
    Returns aggregate and rolling-average cashflow metrics grouped by month.
    Expects queryset of Transaction records. If omitted, uses all included records.
    Tracks healthcare expenses separately for use in retirement projections.
    """
    if queryset is None:
        queryset = Transaction.objects.filter(is_excluded=False)

    monthly = {}
    for tx in queryset.values(
        "date", "amount", "category__is_debt_service", "category__is_medical_expense"
    ):
        d = tx["date"]
        amount = tx["amount"] or Decimal("0")
        key = f"{d.year:04d}-{d.month:02d}"
        if key not in monthly:
            monthly[key] = {
                "income": Decimal("0"),
                "expenses": Decimal("0"),
                "healthcare": Decimal("0"),
            }
        if amount >= 0:
            monthly[key]["income"] += amount
        else:
            if exclude_debt_service and tx.get("category__is_debt_service"):
                continue
            monthly[key]["expenses"] += abs(amount)
            if tx.get("category__is_medical_expense"):
                monthly[key]["healthcare"] += abs(amount)

    agg_income = sum((m["income"] for m in monthly.values()), Decimal("0"))
    agg_expenses = sum((m["expenses"] for m in monthly.values()), Decimal("0"))
    agg_net = agg_income - agg_expenses
    agg_healthcare = sum((m["healthcare"] for m in monthly.values()), Decimal("0"))

    month_count = len(monthly)
    if month_count:
        avg_income = agg_income / month_count
        avg_expenses = agg_expenses / month_count
        avg_net = agg_net / month_count
        avg_healthcare = agg_healthcare / month_count
    else:
        avg_income = Decimal("0")
        avg_expenses = Decimal("0")
        avg_net = Decimal("0")
        avg_healthcare = Decimal("0")

    return {
        "months_count": month_count,
        "aggregate_income": agg_income,
        "aggregate_expenses": agg_expenses,
        "aggregate_net": agg_net,
        "rolling_avg_income": avg_income,
        "rolling_avg_expenses": avg_expenses,
        "rolling_avg_net": avg_net,
        "rolling_avg_healthcare_expenses": avg_healthcare,
    }
