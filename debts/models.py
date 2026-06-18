from django.db import models


class Loan(models.Model):
    LOAN_TYPES = [
        ("mortgage", "Mortgage / Real Estate"),
        ("car", "Car Loan"),
        ("student", "Student Loan"),
        ("other", "Other / Personal Loan"),
    ]
    loan_type = models.CharField(max_length=20, choices=LOAN_TYPES)
    description = models.CharField(
        max_length=200,
        help_text="e.g. 'Primary Residence', '2022 Toyota Highlander'",
    )
    # Real estate only
    property_estimated_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Current estimated market value (real estate only)",
    )
    expected_home_value_growth_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected annual home value increase % (mortgage loans only).",
    )
    is_primary_residence = models.BooleanField(
        default=False,
        help_text="Check if this is your primary residence. Primary residence equity is excluded from investable asset totals (shown separately). Non-primary/investment properties are included in asset calculations.",
    )
    # Loan details
    original_balance = models.DecimalField(max_digits=14, decimal_places=2)
    current_balance = models.DecimalField(max_digits=14, decimal_places=2)
    interest_rate_pct = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        help_text="Annual interest rate %, e.g. 6.750",
    )
    origination_date = models.DateField()
    maturity_date = models.DateField()
    monthly_payment = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total monthly payment (P+I, or P+I+escrow if applicable)",
    )
    is_active = models.BooleanField(default=True)

    # Mortgage-specific: insurance and taxes
    is_escrowed = models.BooleanField(
        default=False,
        help_text="Check if monthly payment includes escrowed insurance + taxes (mortgage only)",
    )
    homeowners_insurance_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual homeowners insurance premium (mortgage only). These costs continue after loan payoff.",
    )
    real_estate_tax_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual real estate property tax (mortgage only). These costs continue after loan payoff.",
    )

    # Car-specific: insurance
    car_insurance_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual car insurance premium (car loan only). This cost continues after loan payoff.",
    )

    class Meta:
        ordering = ["loan_type", "description"]

    def __str__(self):
        return f"{self.description} ({self.get_loan_type_display()})"

    @property
    def equity(self):
        """For real estate: estimated value minus current balance."""
        if self.property_estimated_value:
            return self.property_estimated_value - self.current_balance
        return None


class DebtInfo(models.Model):
    CAR_INSURANCE_FREQUENCY_CHOICES = [
        ("monthly", "Monthly"),
        ("semiannual", "Bi-Yearly (Every 6 Months)"),
        ("yearly", "Yearly"),
    ]

    homeowners_insurance_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual homeowners insurance premium for the home.",
    )
    real_estate_tax_yearly = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual real estate property tax amount.",
    )
    car_insurance_total_premium = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Single total insurance premium for all vehicles in the household.",
    )
    car_insurance_frequency = models.CharField(
        max_length=12,
        choices=CAR_INSURANCE_FREQUENCY_CHOICES,
        default="monthly",
    )

    @classmethod
    def get(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj

    def __str__(self):
        return "Debt Info"
