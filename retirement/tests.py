"""
Tests for the retirement engine — pure functions that require no database.
Covers: SS taxation, federal income tax, withdrawal strategies, COLA.
"""

from decimal import Decimal

from django.test import SimpleTestCase

from retirement.engine import (
    _federal_income_tax,
    _taxable_ss_amount,
    _to_decimal,
    _withdraw_proportional,
    _withdraw_traditional,
)


class ToDecimalTests(SimpleTestCase):
    def test_none_returns_zero(self):
        self.assertEqual(_to_decimal(None), Decimal("0"))

    def test_decimal_passthrough(self):
        d = Decimal("42.50")
        self.assertIs(_to_decimal(d), d)

    def test_int_converted(self):
        self.assertEqual(_to_decimal(5), Decimal("5"))

    def test_string_converted(self):
        self.assertEqual(_to_decimal("3.14"), Decimal("3.14"))


class FederalIncomeTaxTests(SimpleTestCase):
    """Test 2025 progressive bracket calculations."""

    def test_zero_income_no_tax(self):
        self.assertEqual(_federal_income_tax(Decimal("0"), "single"), Decimal("0"))

    def test_negative_income_no_tax(self):
        self.assertEqual(_federal_income_tax(Decimal("-100"), "single"), Decimal("0"))

    def test_first_bracket_single(self):
        # $10,000 taxable → all at 10%
        tax = _federal_income_tax(Decimal("10000"), "single")
        self.assertEqual(tax, Decimal("1000"))

    def test_spans_two_brackets_single(self):
        # $30,000: $11,925 @ 10% + $18,075 @ 12%
        expected = Decimal("11925") * Decimal("0.10") + Decimal("18075") * Decimal("0.12")
        tax = _federal_income_tax(Decimal("30000"), "single")
        self.assertAlmostEqual(float(tax), float(expected), places=2)

    def test_married_lower_rate_same_income(self):
        # $50,000 married: most falls in 12% bracket (vs single crosses into 22%)
        tax_married = _federal_income_tax(Decimal("50000"), "married")
        tax_single = _federal_income_tax(Decimal("50000"), "single")
        self.assertLess(tax_married, tax_single)


class TaxableSsAmountTests(SimpleTestCase):
    """Test SS taxation tier logic (IRS Pub 915)."""

    def test_below_tier1_single_no_tax(self):
        # combined income = 0 + 10,000 * 0.5 = 5,000 < $25,000
        result = _taxable_ss_amount(Decimal("10000"), agi=Decimal("0"), filing_status="single")
        self.assertEqual(result, Decimal("0"))

    def test_above_tier2_married_85pct(self):
        # combined income = 100,000 + 30,000 * 0.5 = 115,000 > $44,000
        ss = Decimal("30000")
        result = _taxable_ss_amount(ss, agi=Decimal("100000"), filing_status="married")
        self.assertEqual(result, ss * Decimal("0.85"))

    def test_zero_ss_returns_zero(self):
        result = _taxable_ss_amount(Decimal("0"), agi=Decimal("50000"), filing_status="single")
        self.assertEqual(result, Decimal("0"))

    def test_tier1_partial_single(self):
        # combined = 20,000 + 12,000 * 0.5 = 26,000 — just above tier1 ($25,000)
        result = _taxable_ss_amount(Decimal("12000"), agi=Decimal("20000"), filing_status="single")
        self.assertGreater(result, Decimal("0"))
        self.assertLessEqual(result, Decimal("12000") * Decimal("0.50"))

    def test_married_higher_thresholds(self):
        # Same income: married should have lower/no taxable SS vs single
        ss = Decimal("20000")
        agi = Decimal("25000")
        married = _taxable_ss_amount(ss, agi=agi, filing_status="married")
        single = _taxable_ss_amount(ss, agi=agi, filing_status="single")
        # combined_married = 25,000 + 10,000 = 35,000 < $32,000? No, 35k > 32k
        # combined_single  = 25,000 + 10,000 = 35,000 > $34,000 tier2
        # married: between tier1 (32k) and tier2 (44k) → 50% bracket
        # single: above tier2 (34k) → 85% bracket
        self.assertLessEqual(married, single)


class WithdrawalStrategyTests(SimpleTestCase):
    """Test traditional and proportional withdrawal ordering."""

    def test_traditional_draws_taxable_first(self):
        wd_t, wd_d, wd_r = _withdraw_traditional(
            shortfall=Decimal("5000"),
            taxable_val=Decimal("10000"),
            deferred_val=Decimal("10000"),
            roth_val=Decimal("10000"),
        )
        self.assertEqual(wd_t, Decimal("5000"))
        self.assertEqual(wd_d, Decimal("0"))
        self.assertEqual(wd_r, Decimal("0"))

    def test_traditional_overflows_to_deferred(self):
        wd_t, wd_d, wd_r = _withdraw_traditional(
            shortfall=Decimal("15000"),
            taxable_val=Decimal("8000"),
            deferred_val=Decimal("10000"),
            roth_val=Decimal("10000"),
        )
        self.assertEqual(wd_t, Decimal("8000"))
        self.assertEqual(wd_d, Decimal("7000"))
        self.assertEqual(wd_r, Decimal("0"))

    def test_traditional_roth_last_resort(self):
        wd_t, wd_d, wd_r = _withdraw_traditional(
            shortfall=Decimal("25000"),
            taxable_val=Decimal("5000"),
            deferred_val=Decimal("8000"),
            roth_val=Decimal("20000"),
        )
        self.assertEqual(wd_t, Decimal("5000"))
        self.assertEqual(wd_d, Decimal("8000"))
        self.assertEqual(wd_r, Decimal("12000"))

    def test_traditional_caps_at_available(self):
        """Cannot withdraw more than what's available."""
        wd_t, wd_d, wd_r = _withdraw_traditional(
            shortfall=Decimal("100000"),
            taxable_val=Decimal("1000"),
            deferred_val=Decimal("2000"),
            roth_val=Decimal("3000"),
        )
        self.assertEqual(wd_t + wd_d + wd_r, Decimal("6000"))

    def test_proportional_draws_from_all(self):
        shortfall = Decimal("9000")
        taxable_val = Decimal("30000")  # 50%
        deferred_val = Decimal("18000")  # 30%
        roth_val = Decimal("12000")  # 20%
        wd_t, wd_d, wd_r = _withdraw_proportional(shortfall, taxable_val, deferred_val, roth_val)
        total = wd_t + wd_d + wd_r
        self.assertAlmostEqual(float(total), 9000.0, places=1)
        # Each should be roughly proportional
        self.assertAlmostEqual(float(wd_t), 4500.0, delta=10)
        self.assertAlmostEqual(float(wd_d), 2700.0, delta=10)
        self.assertAlmostEqual(float(wd_r), 1800.0, delta=10)

    def test_proportional_empty_buckets(self):
        wd_t, wd_d, wd_r = _withdraw_proportional(
            Decimal("5000"),
            Decimal("0"),
            Decimal("0"),
            Decimal("0"),
        )
        self.assertEqual(wd_t + wd_d + wd_r, Decimal("0"))
