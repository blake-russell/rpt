from django.db import models


class W2Income(models.Model):
    person = models.ForeignKey("people.Person", on_delete=models.CASCADE, related_name="w2_incomes")
    employer = models.CharField(max_length=200)
    annual_salary = models.DecimalField(max_digits=12, decimal_places=2)
    effective_date = models.DateField(help_text="Date this salary became effective")
    is_current = models.BooleanField(default=True)

    class Meta:
        ordering = ["-effective_date"]

    def __str__(self):
        return f"{self.person.name} — {self.employer} (${self.annual_salary:,})"


class Bonus(models.Model):
    BONUS_TYPE = [("flat", "Flat Amount"), ("pct", "Percentage of Salary")]
    w2 = models.ForeignKey(W2Income, on_delete=models.CASCADE, related_name="bonuses")
    bonus_type = models.CharField(max_length=4, choices=BONUS_TYPE)
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Dollar amount if flat; percentage (e.g. 10.00 for 10%) if pct",
    )
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        if self.bonus_type == "flat":
            return f"${self.amount:,} flat bonus"
        return f"{self.amount}% bonus"

    def resolved_amount(self):
        """Return dollar value of bonus."""
        if self.bonus_type == "flat":
            return self.amount
        return (self.w2.annual_salary * self.amount / 100).quantize(self.amount)


class RaiseSchedule(models.Model):
    RAISE_TYPE = [("annual_pct", "Annual % Raise"), ("one_time", "One-Time Raise in Year")]
    person = models.ForeignKey(
        "people.Person", on_delete=models.CASCADE, related_name="raise_schedules"
    )
    raise_type = models.CharField(max_length=10, choices=RAISE_TYPE)
    annual_pct = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Annual raise % (e.g. 3.00 for 3%)",
    )
    one_time_year = models.IntegerField(
        null=True,
        blank=True,
        help_text="Year the one-time raise occurs",
    )
    one_time_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="New salary amount in that year",
    )

    def __str__(self):
        if self.raise_type == "annual_pct":
            return f"{self.person.name} — {self.annual_pct}% annual raise"
        return f"{self.person.name} — one-time raise to ${self.one_time_amount:,} in {self.one_time_year}"


class SocialSecurity(models.Model):
    """
    SSA benefit estimates per earner, entered manually from ssa.gov statement.
    One record per person (user/spouse only). Retirement engine uses
    claimed_age + person.birth_year to determine when SS income starts.
    """

    CLAIM_AGE_CHOICES = [
        (62, "Age 62 (Early — reduced benefit)"),
        (63, "Age 63"),
        (64, "Age 64"),
        (65, "Age 65"),
        (66, "Age 66"),
        (67, "Age 67 (Full Retirement Age for most)"),
        (68, "Age 68"),
        (69, "Age 69"),
        (70, "Age 70 (Maximum — delayed benefit)"),
    ]

    person = models.OneToOneField(
        "people.Person",
        on_delete=models.CASCADE,
        related_name="social_security",
        limit_choices_to={"role__in": ["user", "spouse"]},
    )
    # Benefit estimates from ssa.gov statement (monthly, in today's dollars)
    monthly_benefit_age_62 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated monthly benefit if claimed at age 62 (from ssa.gov)",
    )
    monthly_benefit_fra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated monthly benefit at Full Retirement Age — typically 67 (from ssa.gov)",
    )
    monthly_benefit_age_70 = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Estimated monthly benefit if claimed at age 70 (from ssa.gov)",
    )
    # Which age this person plans to start claiming
    planned_claim_age = models.IntegerField(
        choices=CLAIM_AGE_CHOICES,
        default=67,
        help_text="Age you plan to start collecting Social Security",
    )

    def __str__(self):
        return f"{self.person.name} — Social Security (claim at {self.planned_claim_age})"

    @property
    def planned_monthly_benefit(self):
        """Return the benefit amount corresponding to the planned claim age."""
        if self.planned_claim_age <= 62:
            return self.monthly_benefit_age_62
        elif self.planned_claim_age >= 70:
            return self.monthly_benefit_age_70
        else:
            # Interpolate linearly between age-62 and FRA (62→67),
            # or FRA and age-70 (67→70).
            if self.monthly_benefit_age_62 and self.monthly_benefit_fra:
                fra = 67
                if self.planned_claim_age <= fra:
                    span = fra - 62
                    step = (self.monthly_benefit_fra - self.monthly_benefit_age_62) / span
                    return self.monthly_benefit_age_62 + step * (self.planned_claim_age - 62)
                elif self.monthly_benefit_age_70 and self.monthly_benefit_fra:
                    span = 70 - fra
                    step = (self.monthly_benefit_age_70 - self.monthly_benefit_fra) / span
                    return self.monthly_benefit_fra + step * (self.planned_claim_age - fra)
            return self.monthly_benefit_fra

    @property
    def planned_claim_year(self):
        if self.person.birth_year:
            return self.person.birth_year + self.planned_claim_age
        return None

    @property
    def annual_benefit(self):
        benefit = self.planned_monthly_benefit
        return benefit * 12 if benefit else None
