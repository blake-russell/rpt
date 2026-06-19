from django import forms

from debts.models import Loan

from .models import RetirementSettings


class RetirementSettingsForm(forms.ModelForm):
    class Meta:
        model = RetirementSettings
        fields = [
            "portfolio_growth_rate_pct",
            "expenses_annual_growth_pct",
            "ss_cola_pct",
            "healthcare_inflation_pct",
            "use_budget_cashflow_for_income",
            "dependent_leave_expense_reduction_pct",
            "withdrawal_strategy",
        ]
        widgets = {
            "portfolio_growth_rate_pct": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "expenses_annual_growth_pct": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "ss_cola_pct": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "10"}),
            "healthcare_inflation_pct": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "20"}
            ),
            "dependent_leave_expense_reduction_pct": forms.NumberInput(
                attrs={"step": "0.01", "min": "0", "max": "100"}
            ),
        }
        labels = {
            "portfolio_growth_rate_pct": "Portfolio Growth Rate (%)",
            "expenses_annual_growth_pct": "CPI / Expense Growth Rate (%)",
            "ss_cola_pct": "Social Security COLA (%)",
            "healthcare_inflation_pct": "Healthcare Inflation Rate (%)",
            "use_budget_cashflow_for_income": "Use budget cashflow for expense baseline",
            "dependent_leave_expense_reduction_pct": "Expense reduction when dependents leave (%)",
            "withdrawal_strategy": "Withdrawal Strategy",
        }


class PayoffScenarioForm(forms.Form):
    loan = forms.ModelChoiceField(queryset=Loan.objects.none())
    years_early = forms.IntegerField(min_value=1, max_value=40, initial=5)
    versus_return_pct = forms.DecimalField(
        min_value=0,
        max_digits=5,
        decimal_places=2,
        initial=7.00,
        help_text="Comparison annual return % (e.g. 7.00 for conservative S&P 500 baseline).",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["loan"].queryset = Loan.objects.filter(is_active=True).order_by(
            "loan_type", "description"
        )
