from decimal import Decimal

from django.db import models

# ── Annual Rate Defaults ──────────────────────────────────────────────────────
# Update these constants when government / industry releases new annual estimates.
# They become the initial defaults for new RetirementSettings singletons.
DEFAULT_PORTFOLIO_GROWTH_PCT = Decimal("7.00")  # Historical S&P 500 avg ~10%, conservative 5–7%
DEFAULT_EXPENSES_CPI_PCT = Decimal("3.00")  # CPI-E avg ~3–4%
DEFAULT_SS_COLA_PCT = Decimal("2.50")  # CPI-W historical avg ~2–3%; see ssa.gov/news/cola
DEFAULT_HEALTHCARE_INFLATION_PCT = Decimal("4.50")  # Medical CPI historically ~3–6% annually


class RetirementSettings(models.Model):
    target_retirement_year = models.IntegerField(default=2045)
    target_life_expectancy_year = models.IntegerField(default=2065)
    annual_spending_today = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=80000,
        help_text="Annual non-debt retirement spending in today's dollars. Debt payments are auto-calculated from the Debts module.",
    )
    portfolio_growth_rate_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_PORTFOLIO_GROWTH_PCT,
        help_text="Annual portfolio growth %. Historical S&P 500 avg ~10%; conservative long-term estimate 5–7%. Default: 7%.",
    )
    expenses_annual_growth_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_EXPENSES_CPI_PCT,
        help_text="Annual consumer expense inflation % (CPI-E). Historical avg ~3–4%; Applies to consumer expenses only, NOT debt service. Default: 3%.",
    )
    ss_cola_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_SS_COLA_PCT,
        help_text="Annual Social Security COLA % (CPI-W). Historical avg ~2–3%. Updated each October by SSA. See ssa.gov/news/cola. Default: 2.5%.",
    )
    healthcare_inflation_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=DEFAULT_HEALTHCARE_INFLATION_PCT,
        help_text="Annual healthcare cost inflation % (Medical CPI). Historically ~3–6% annually — significantly outpaces general CPI. Stored for future healthcare expense projections. Default: 4.5%.",
    )
    use_budget_cashflow_for_income = models.BooleanField(
        default=True,
        help_text="Use budget rolling-average monthly cashflow for income baseline (recommended). When checked, income is derived from your imported budget transactions.",
    )
    dependent_leave_expense_reduction_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=10,
        help_text="Percent reduction in annual consumer expenses when each dependent reaches move-out age. Typical household savings: 8–15% per dependent. Default: 10%.",
    )
    withdrawal_strategy = models.CharField(
        max_length=20,
        choices=[
            ("traditional", "Traditional Sequence (taxable → tax-deferred → Roth)"),
            ("proportional", "Proportional (draw from all buckets by share)"),
        ],
        default="traditional",
        help_text="Traditional: withdraws from taxable accounts first, preserving Roth growth longest — simple, most common. Proportional: draws from all buckets simultaneously by share — smoother tax bill, potentially lower lifetime taxes.",
    )

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Retirement Settings"
