from django import forms

from people.models import Person

from .models import Bonus, RaiseSchedule, SocialSecurity, W2Income


class W2IncomeForm(forms.ModelForm):
    # ── Inline bonus fields ───────────────────────────────────────────────────
    bonus_type = forms.ChoiceField(
        choices=[("", "— No bonus —"), ("flat", "Flat Amount ($)"), ("pct", "% of Base Salary")],
        required=False,
        label="Bonus / Incentive Type",
    )
    bonus_amount = forms.DecimalField(
        required=False,
        max_digits=12,
        decimal_places=2,
        label="Bonus Amount",
        help_text="Dollar amount if flat; percentage value (e.g. 10.00 for 10%) if % of salary.",
        widget=forms.NumberInput(
            attrs={"placeholder": "e.g. 5000 or 10.00", "step": "0.01", "min": "0"}
        ),
    )
    bonus_description = forms.CharField(
        required=False,
        max_length=200,
        label="Bonus Description",
        widget=forms.TextInput(attrs={"placeholder": "e.g. Annual performance bonus"}),
    )

    # ── Inline merit increase ─────────────────────────────────────────────────
    annual_merit_pct = forms.DecimalField(
        required=False,
        max_digits=5,
        decimal_places=2,
        label="Expected Annual Merit Increase (%)",
        help_text="Yearly % raise applied to base salary (e.g. 3.00 for 3%). Saved as a raise schedule.",
        widget=forms.NumberInput(
            attrs={"placeholder": "e.g. 3.00", "step": "0.01", "min": "0", "max": "100"}
        ),
    )

    class Meta:
        model = W2Income
        fields = ["person", "employer", "annual_salary", "effective_date", "is_current"]
        widgets = {
            "effective_date": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only user/spouse can have W2 income
        self.fields["person"].queryset = Person.objects.filter(role__in=["user", "spouse"])

        # Pre-populate inline fields from existing related records on edit
        if self.instance and self.instance.pk:
            existing_bonus = self.instance.bonuses.first()
            if existing_bonus:
                self.fields["bonus_type"].initial = existing_bonus.bonus_type
                self.fields["bonus_amount"].initial = existing_bonus.amount
                self.fields["bonus_description"].initial = existing_bonus.description

            existing_raise = (
                self.instance.person_id
                and RaiseSchedule.objects.filter(
                    person_id=self.instance.person_id,
                    raise_type="annual_pct",
                ).first()
                if self.instance.person_id
                else None
            )
            if existing_raise:
                self.fields["annual_merit_pct"].initial = existing_raise.annual_pct


class BonusForm(forms.ModelForm):
    class Meta:
        model = Bonus
        fields = ["w2", "bonus_type", "amount", "description"]


class RaiseScheduleForm(forms.ModelForm):
    class Meta:
        model = RaiseSchedule
        fields = ["person", "raise_type", "annual_pct", "one_time_year", "one_time_amount"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.filter(role__in=["user", "spouse"])


class SocialSecurityForm(forms.ModelForm):
    class Meta:
        model = SocialSecurity
        fields = [
            "person",
            "monthly_benefit_age_62",
            "monthly_benefit_fra",
            "monthly_benefit_age_70",
            "planned_claim_age",
        ]
        labels = {
            "monthly_benefit_age_62": "Monthly benefit at age 62 ($)",
            "monthly_benefit_fra": "Monthly benefit at Full Retirement Age ($)",
            "monthly_benefit_age_70": "Monthly benefit at age 70 ($)",
        }
        help_texts = {
            "monthly_benefit_age_62": "From your ssa.gov statement — early reduced benefit.",
            "monthly_benefit_fra": "From your ssa.gov statement — full retirement age (typically 67).",
            "monthly_benefit_age_70": "From your ssa.gov statement — maximum delayed benefit.",
            "planned_claim_age": "The retirement engine will add SS income starting this age.",
        }
        widgets = {
            "monthly_benefit_age_62": forms.NumberInput(
                attrs={"placeholder": "e.g. 1850", "step": "0.01", "min": "0"}
            ),
            "monthly_benefit_fra": forms.NumberInput(
                attrs={"placeholder": "e.g. 2400", "step": "0.01", "min": "0"}
            ),
            "monthly_benefit_age_70": forms.NumberInput(
                attrs={"placeholder": "e.g. 3100", "step": "0.01", "min": "0"}
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["person"].queryset = Person.objects.filter(role__in=["user", "spouse"])
