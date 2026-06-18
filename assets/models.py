from django.db import models


class Account(models.Model):
    ACCOUNT_TYPES = [
        ("brokerage", "Brokerage"),
        ("ira", "Traditional IRA"),
        ("401k", "401(k) Traditional"),
        ("roth_ira", "Roth IRA"),
        ("roth_401k", "Roth 401(k)"),
        ("crypto", "Crypto"),
        ("other", "Other"),
    ]
    name = models.CharField(max_length=200, help_text="e.g. 'Fidelity Brokerage'")
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    institution = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["account_type", "name"]

    def __str__(self):
        return f"{self.name} ({self.get_account_type_display()})"

    @property
    def total_value(self):
        vals = [h.current_value for h in self.holdings.all() if h.current_value is not None]
        return sum(vals) if vals else None

    @property
    def total_cost_basis(self):
        return sum(h.total_cost_basis for h in self.holdings.all())

    @property
    def monthly_contribution_total(self):
        return sum(c.monthly_amount for h in self.holdings.all() for c in h.contributions.all())


class Holding(models.Model):
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="holdings")
    ticker = models.CharField(max_length=20, help_text="Stock/ETF/crypto ticker symbol")
    name = models.CharField(max_length=200, blank=True, help_text="Human-readable name")
    shares = models.DecimalField(max_digits=20, decimal_places=6)
    avg_cost_basis = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        help_text="Average cost per share across all purchases",
    )
    last_price = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    last_price_updated = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["ticker"]

    def __str__(self):
        return f"{self.ticker} — {self.account.name}"

    @property
    def current_value(self):
        if self.last_price:
            return self.shares * self.last_price
        return None

    @property
    def total_cost_basis(self):
        return self.shares * self.avg_cost_basis

    @property
    def gain_loss(self):
        if self.current_value is not None:
            return self.current_value - self.total_cost_basis
        return None

    @property
    def gain_loss_pct(self):
        basis = self.total_cost_basis
        if self.gain_loss is not None and basis and basis != 0:
            return (self.gain_loss / basis) * 100
        return None


class MonthlyContribution(models.Model):
    holding = models.ForeignKey(Holding, on_delete=models.CASCADE, related_name="contributions")
    monthly_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(
        max_length=200,
        blank=True,
        help_text="e.g. '401k payroll deduction into FSKAX'",
    )

    def __str__(self):
        return f"${self.monthly_amount}/mo → {self.holding.ticker} ({self.holding.account.name})"
