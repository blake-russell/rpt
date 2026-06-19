from django import forms

from .models import Loan


class LoanForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = [
            "loan_type",
            "description",
            "property_estimated_value",
            "expected_home_value_growth_pct",
            "is_primary_residence",
            "original_balance",
            "current_balance",
            "interest_rate_pct",
            "origination_date",
            "maturity_date",
            "monthly_payment",
            "is_active",
            "is_escrowed",
            "homeowners_insurance_yearly",
            "real_estate_tax_yearly",
            "car_insurance_yearly",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={"placeholder": "e.g. 'Primary Residence' or '2022 Toyota Highlander'"}
            ),
            "origination_date": forms.DateInput(attrs={"type": "date"}),
            "maturity_date": forms.DateInput(attrs={"type": "date"}),
            "interest_rate_pct": forms.NumberInput(
                attrs={"placeholder": "e.g. 6.750", "step": "0.001", "min": "0"}
            ),
            "original_balance": forms.NumberInput(
                attrs={"placeholder": "e.g. 350000", "step": "0.01", "min": "0"}
            ),
            "current_balance": forms.NumberInput(
                attrs={"placeholder": "e.g. 298500", "step": "0.01", "min": "0"}
            ),
            "monthly_payment": forms.NumberInput(
                attrs={"placeholder": "e.g. 2100.00", "step": "0.01", "min": "0"}
            ),
            "property_estimated_value": forms.NumberInput(
                attrs={"placeholder": "e.g. 420000", "step": "0.01", "min": "0"}
            ),
            "expected_home_value_growth_pct": forms.NumberInput(
                attrs={"placeholder": "e.g. 3.50", "step": "0.01", "min": "0"}
            ),
            "homeowners_insurance_yearly": forms.NumberInput(
                attrs={"placeholder": "e.g. 1200", "step": "0.01", "min": "0"}
            ),
            "real_estate_tax_yearly": forms.NumberInput(
                attrs={"placeholder": "e.g. 3600", "step": "0.01", "min": "0"}
            ),
            "car_insurance_yearly": forms.NumberInput(
                attrs={"placeholder": "e.g. 1800", "step": "0.01", "min": "0"}
            ),
        }
        help_texts = {
            "property_estimated_value": "Real estate only — current estimated market value.",
            "expected_home_value_growth_pct": "Used in retirement projections for home value growth assumptions.",
            "interest_rate_pct": "Annual interest rate as a percentage, e.g. 6.750 for 6.75%.",
        }
