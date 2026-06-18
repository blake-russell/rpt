import calendar
from datetime import date
from decimal import Decimal


def _add_months(d, n):
    month = d.month - 1 + n
    year = d.year + month // 12
    month = month % 12 + 1
    day = min(d.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _monthly_rate(loan):
    return loan.interest_rate_pct / Decimal("100") / Decimal("12")


def payoff_schedule(loan):
    """
    Generate the monthly amortization schedule from the current balance forward.
    Returns list of dicts: {date, payment, principal, interest, balance}
    """
    schedule = []
    balance = loan.current_balance
    monthly_rate = _monthly_rate(loan)
    payment = loan.monthly_payment
    today = date.today()
    # Start from the first day of next month
    current = date(today.year, today.month, 1)
    current = _add_months(current, 1)
    maturity = loan.maturity_date

    while balance > 0 and current <= maturity:
        interest = (balance * monthly_rate).quantize(Decimal("0.01"))
        principal = min(payment - interest, balance)
        balance = max(balance - principal, Decimal("0"))
        schedule.append(
            {
                "date": current,
                "payment": payment,
                "principal": principal.quantize(Decimal("0.01")),
                "interest": interest,
                "balance": balance.quantize(Decimal("0.01")),
            }
        )
        current = _add_months(current, 1)

    return schedule


def project_balance(loan, target_date):
    """
    Return remaining balance at target_date via amortization from current_balance.
    Returns Decimal('0') if paid off.
    """
    if target_date <= date.today():
        return loan.current_balance

    balance = loan.current_balance
    monthly_rate = _monthly_rate(loan)
    payment = loan.monthly_payment
    today = date.today()
    current = date(today.year, today.month, 1)
    target = date(target_date.year, target_date.month, 1)

    while current < target and balance > 0:
        interest = (balance * monthly_rate).quantize(Decimal("0.01"))
        principal = min(payment - interest, balance)
        balance = max(balance - principal, Decimal("0"))
        current = _add_months(current, 1)

    return balance.quantize(Decimal("0.01"))
