"""
Tests for the debts app — amortization, project_balance, and loan model.
"""

from datetime import date
from decimal import Decimal

from django.test import TestCase

from debts.models import Loan
from debts.utils import payoff_schedule, project_balance


def _make_loan(**kwargs):
    today = date.today()
    defaults = {
        "loan_type": "car",
        "description": "Test Car",
        "original_balance": Decimal("20000"),
        "current_balance": Decimal("20000"),
        "interest_rate_pct": Decimal("6.000"),
        "origination_date": today,
        "maturity_date": date(today.year + 5, today.month, 1),
        "monthly_payment": Decimal("386.66"),
        "is_active": True,
    }
    defaults.update(kwargs)
    return Loan.objects.create(**defaults)


class PayoffScheduleTests(TestCase):
    def test_schedule_non_empty(self):
        loan = _make_loan()
        schedule = payoff_schedule(loan)
        self.assertGreater(len(schedule), 0)

    def test_balance_reaches_zero(self):
        loan = _make_loan()
        schedule = payoff_schedule(loan)
        self.assertEqual(schedule[-1]["balance"], Decimal("0"))

    def test_first_payment_has_interest(self):
        loan = _make_loan()
        schedule = payoff_schedule(loan)
        self.assertGreater(schedule[0]["interest"], Decimal("0"))

    def test_each_payment_reduces_balance(self):
        loan = _make_loan()
        schedule = payoff_schedule(loan)
        for i in range(1, len(schedule)):
            self.assertLess(schedule[i]["balance"], schedule[i - 1]["balance"])

    def test_zero_interest_loan(self):
        loan = _make_loan(interest_rate_pct=Decimal("0.000"), monthly_payment=Decimal("400"))
        schedule = payoff_schedule(loan)
        for row in schedule:
            self.assertEqual(row["interest"], Decimal("0"))


class ProjectBalanceTests(TestCase):
    def test_past_date_returns_current_balance(self):
        loan = _make_loan(current_balance=Decimal("15000"))
        past = date(2020, 1, 1)
        self.assertEqual(project_balance(loan, past), Decimal("15000"))

    def test_future_date_reduces_balance(self):
        loan = _make_loan()
        future = date(date.today().year + 2, 1, 1)
        balance = project_balance(loan, future)
        self.assertLess(balance, Decimal("20000"))
        self.assertGreaterEqual(balance, Decimal("0"))

    def test_beyond_maturity_returns_zero(self):
        loan = _make_loan()
        far_future = date(2050, 1, 1)
        self.assertEqual(project_balance(loan, far_future), Decimal("0"))


class LoanModelTests(TestCase):
    def test_equity_property_for_mortgage(self):
        loan = Loan.objects.create(
            loan_type="mortgage",
            description="Home",
            property_estimated_value=Decimal("400000"),
            original_balance=Decimal("300000"),
            current_balance=Decimal("250000"),
            interest_rate_pct=Decimal("5.000"),
            origination_date=date(2020, 1, 1),
            maturity_date=date(2050, 1, 1),
            monthly_payment=Decimal("1610"),
            is_active=True,
        )
        self.assertEqual(loan.equity, Decimal("150000"))

    def test_equity_none_without_estimated_value(self):
        loan = _make_loan(loan_type="mortgage")
        self.assertIsNone(loan.equity)
